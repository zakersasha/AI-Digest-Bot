import asyncio
import email
import imaplib
import json
from datetime import UTC, datetime
from email.header import decode_header
from email.utils import parseaddr, parsedate_to_datetime
from urllib.parse import urlencode

import httpx

from app.config import Settings
from app.services.content_message import ContentMessage
from app.utils.crypto import decrypt_session, encrypt_session
from app.utils.logging import get_logger

logger = get_logger(__name__)

# Read-only IMAP — matches «Доступ на чтение писем в почтовом ящике» in oauth.yandex.ru
YANDEX_DEFAULT_SCOPES = "mail:imap_ro"
YANDEX_AUTH_URL = "https://oauth.yandex.ru/authorize"
YANDEX_TOKEN_URL = "https://oauth.yandex.ru/token"
YANDEX_USERINFO_URL = "https://login.yandex.ru/info"
YANDEX_VERIFICATION_REDIRECT = "https://oauth.yandex.ru/verification_code"
IMAP_HOST = "imap.yandex.com"


class YandexImapError(Exception):
    def __init__(self, code: str, detail: str = "") -> None:
        self.code = code
        super().__init__(detail or code)


class YandexMailService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def is_configured(self) -> bool:
        return bool(self._settings.yandex_client_id and self._settings.yandex_client_secret)

    def build_auth_url(self, state: str) -> str:
        params = {
            "response_type": "code",
            "client_id": self._settings.yandex_client_id,
            "redirect_uri": self._settings.yandex_redirect_uri,
            "state": state,
            "force_confirm": "yes",
        }
        scopes = (self._settings.yandex_oauth_scopes or "").strip()
        if scopes:
            params["scope"] = scopes
        return f"{YANDEX_AUTH_URL}?{urlencode(params)}"

    async def exchange_code(self, code: str) -> dict:
        payload = {
            "grant_type": "authorization_code",
            "code": code,
            "client_id": self._settings.yandex_client_id,
            "client_secret": self._settings.yandex_client_secret,
            "redirect_uri": self._settings.yandex_redirect_uri,
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(YANDEX_TOKEN_URL, data=payload)
            response.raise_for_status()
            return response.json()

    async def refresh_access_token(self, refresh_token: str) -> dict:
        payload = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": self._settings.yandex_client_id,
            "client_secret": self._settings.yandex_client_secret,
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(YANDEX_TOKEN_URL, data=payload)
            response.raise_for_status()
            return response.json()

    @staticmethod
    def encrypt_tokens(tokens: dict) -> str:
        return encrypt_session(json.dumps(tokens))

    @staticmethod
    def decrypt_tokens(encrypted: str) -> dict:
        try:
            return json.loads(decrypt_session(encrypted))
        except ValueError as exc:
            if "Invalid encrypted session" in str(exc):
                raise ValueError("yandex_token_invalid") from exc
            raise

    async def get_access_token(self, encrypted_tokens: str) -> tuple[str, dict]:
        tokens = self.decrypt_tokens(encrypted_tokens)
        access = tokens.get("access_token")
        expires_at = tokens.get("expires_at", 0)
        if access and expires_at > datetime.now(tz=UTC).timestamp() + 60:
            return access, tokens

        refresh = tokens.get("refresh_token")
        if not refresh:
            raise ValueError("yandex_token_expired")

        try:
            refreshed = await self.refresh_access_token(refresh)
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code in (400, 401):
                raise ValueError("yandex_token_expired") from exc
            raise
        tokens["access_token"] = refreshed["access_token"]
        tokens["expires_at"] = datetime.now(tz=UTC).timestamp() + int(refreshed.get("expires_in", 3600))
        if refreshed.get("refresh_token"):
            tokens["refresh_token"] = refreshed["refresh_token"]
        return tokens["access_token"], tokens

    async def resolve_account_email(self, access_token: str) -> str:
        profile = await self._fetch_profile(access_token)
        return profile.get("email") or ""

    async def _fetch_profile(self, access_token: str) -> dict[str, str]:
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    YANDEX_USERINFO_URL,
                    params={"format": "json"},
                    headers={"Authorization": f"OAuth {access_token}"},
                )
                if response.status_code != 200:
                    return {}
                data = response.json()
        except httpx.HTTPError:
            logger.warning("yandex_userinfo_failed")
            return {}

        login = (data.get("login") or "").strip()
        email = (data.get("default_email") or "").strip()
        if not email and login and "@" not in login:
            email = f"{login}@yandex.ru"
        elif not email:
            email = login

        return {"email": email, "login": login}

    async def fetch_messages(
        self,
        encrypted_tokens: str,
        since: datetime,
        max_messages: int,
    ) -> tuple[list[ContentMessage], dict]:
        access_token, tokens = await self.get_access_token(encrypted_tokens)
        login = tokens.get("login")
        email_addr = tokens.get("email")
        if not email_addr or not login:
            profile = await self._fetch_profile(access_token)
            email_addr = email_addr or profile.get("email", "")
            login = login or profile.get("login")
        if not email_addr:
            raise ValueError("yandex_email_unresolved")
        tokens["email"] = email_addr
        if login:
            tokens["login"] = login

        try:
            messages = await asyncio.to_thread(
                _fetch_imap_messages,
                email_addr,
                access_token,
                since,
                max_messages,
                login,
            )
        except YandexImapError as exc:
            raise ValueError(exc.code) from exc
        logger.info("yandex_messages_fetched", count=len(messages), since=since.isoformat())
        return messages, tokens

    async def complete_oauth(self, code: str) -> tuple[dict, str]:
        raw = await self.exchange_code(code)
        expires_at = datetime.now(tz=UTC).timestamp() + int(raw.get("expires_in", 3600))
        tokens = {
            "access_token": raw["access_token"],
            "refresh_token": raw.get("refresh_token"),
            "expires_at": expires_at,
        }
        email_addr = await self.resolve_account_email(tokens["access_token"])
        profile = await self._fetch_profile(tokens["access_token"])
        if profile.get("email"):
            email_addr = profile["email"]
        if profile.get("login"):
            tokens["login"] = profile["login"]
        if email_addr:
            tokens["email"] = email_addr
        return tokens, email_addr or "Yandex Mail"


def yandex_message_url(uid: str) -> str:
    return f"https://mail.yandex.ru/#inbox/{uid}"


def _oauth2_string(username: str, access_token: str) -> bytes:
    user = username.strip()
    token = access_token.strip()
    return f"user={user}\x01auth=Bearer {token}\x01\x01".encode()


def _imap_email_candidates(email_addr: str, login: str | None) -> list[str]:
    candidates: list[str] = []
    seen: set[str] = set()

    def add(addr: str | None) -> None:
        addr = (addr or "").strip()
        if not addr or addr in seen:
            return
        seen.add(addr)
        candidates.append(addr)

    add(email_addr)
    if login:
        login = login.strip()
        if "@" in login:
            add(login)
        else:
            for domain in ("yandex.ru", "ya.ru", "yandex.com"):
                add(f"{login}@{domain}")
    return candidates


def _imap_auth_error_code(exc: imaplib.IMAP4.error) -> str:
    text = str(exc).lower()
    if "imap is disabled" in text:
        return "yandex_imap_disabled"
    return "yandex_imap_auth_failed"


def _connect_imap(email_addr: str, access_token: str) -> imaplib.IMAP4_SSL:
    mail = imaplib.IMAP4_SSL(IMAP_HOST, 993)
    mail.authenticate("XOAUTH2", lambda _challenge: _oauth2_string(email_addr, access_token))
    return mail


def _decode_header_value(value: str) -> str:
    parts: list[str] = []
    for chunk, charset in decode_header(value):
        if isinstance(chunk, bytes):
            parts.append(chunk.decode(charset or "utf-8", errors="replace"))
        else:
            parts.append(chunk)
    return "".join(parts).strip()


def _extract_plain_text(msg: email.message.Message) -> str:
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain" and not part.get_content_disposition():
                payload = part.get_payload(decode=True)
                if payload:
                    charset = part.get_content_charset() or "utf-8"
                    return payload.decode(charset, errors="replace").strip()
        for part in msg.walk():
            if part.get_content_type().startswith("text/"):
                payload = part.get_payload(decode=True)
                if payload:
                    charset = part.get_content_charset() or "utf-8"
                    return payload.decode(charset, errors="replace").strip()
        return ""
    payload = msg.get_payload(decode=True)
    if not payload:
        return ""
    charset = msg.get_content_charset() or "utf-8"
    return payload.decode(charset, errors="replace").strip()


def _fetch_imap_messages(
    email_addr: str,
    access_token: str,
    since: datetime,
    max_messages: int,
    login: str | None = None,
) -> list[ContentMessage]:
    last_error: imaplib.IMAP4.error | None = None
    last_code = "yandex_imap_auth_failed"

    for candidate in _imap_email_candidates(email_addr, login):
        mail: imaplib.IMAP4_SSL | None = None
        try:
            mail = _connect_imap(candidate, access_token)
            messages = _read_imap_inbox(mail, since, max_messages)
            if candidate != email_addr:
                logger.info("yandex_imap_email_fallback", email=candidate)
            return messages
        except imaplib.IMAP4.error as exc:
            last_error = exc
            last_code = _imap_auth_error_code(exc)
            logger.warning("yandex_imap_auth_try_failed", email=candidate, error=str(exc))
        finally:
            if mail is not None:
                try:
                    mail.logout()
                except Exception:
                    pass

    raise YandexImapError(last_code, str(last_error) if last_error else last_code)


def _read_imap_inbox(
    mail: imaplib.IMAP4_SSL,
    since: datetime,
    max_messages: int,
) -> list[ContentMessage]:
    mail.select("INBOX")
    since_str = since.strftime("%d-%b-%Y")
    status, data = mail.search(None, f'(SINCE "{since_str}")')
    if status != "OK" or not data or not data[0]:
        return []

    uids = data[0].split()
    uids = uids[-max_messages:]
    messages: list[ContentMessage] = []

    for uid in reversed(uids):
        status, fetched = mail.fetch(uid, "(RFC822)")
        if status != "OK" or not fetched or not fetched[0]:
            continue
        raw = fetched[0][1]
        if not isinstance(raw, (bytes, bytearray)):
            continue
        msg = email.message_from_bytes(raw)
        subject = _decode_header_value(msg.get("Subject", "(no subject)"))
        sender = _decode_header_value(msg.get("From", "unknown"))
        _, addr = parseaddr(sender)
        body = _extract_plain_text(msg)
        if not body:
            continue

        date_hdr = msg.get("Date")
        try:
            msg_date = parsedate_to_datetime(date_hdr) if date_hdr else datetime.now(tz=UTC)
            if msg_date.tzinfo is None:
                msg_date = msg_date.replace(tzinfo=UTC)
        except (TypeError, ValueError):
            msg_date = datetime.now(tz=UTC)

        if msg_date < since:
            continue

        uid_str = uid.decode() if isinstance(uid, bytes) else str(uid)
        label = addr or sender
        text = f"Subject: {subject}\nFrom: {sender}\n\n{body}"
        messages.append(
            ContentMessage(
                text=text,
                source=f"yandex:{label}",
                date=msg_date,
                message_id=uid_str,
                post_url=yandex_message_url(uid_str),
            )
        )
    messages.sort(key=lambda item: item.date)
    return messages
