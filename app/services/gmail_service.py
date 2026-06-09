import base64
import json
from datetime import UTC, datetime
from email.utils import parseaddr
from urllib.parse import urlencode

import httpx

from app.config import Settings
from app.services.content_message import ContentMessage
from app.utils.crypto import decrypt_session, encrypt_session
from app.utils.logging import get_logger

logger = get_logger(__name__)

GMAIL_SCOPES = (
    "https://www.googleapis.com/auth/gmail.readonly "
    "https://www.googleapis.com/auth/userinfo.email"
)
GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GMAIL_API = "https://gmail.googleapis.com/gmail/v1/users/me"


class GmailService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def is_configured(self) -> bool:
        return bool(self._settings.gmail_client_id and self._settings.gmail_client_secret)

    def build_auth_url(self, state: str) -> str:
        params = {
            "client_id": self._settings.gmail_client_id,
            "redirect_uri": self._settings.gmail_redirect_uri,
            "response_type": "code",
            "scope": GMAIL_SCOPES,
            "access_type": "offline",
            "include_granted_scopes": "true",
            "state": state,
        }
        return f"{GOOGLE_AUTH_URL}?{urlencode(params)}"

    async def exchange_code(self, code: str) -> dict:
        payload = {
            "code": code,
            "client_id": self._settings.gmail_client_id,
            "client_secret": self._settings.gmail_client_secret,
            "redirect_uri": self._settings.gmail_redirect_uri,
            "grant_type": "authorization_code",
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(GOOGLE_TOKEN_URL, data=payload)
            response.raise_for_status()
            return response.json()

    async def refresh_access_token(self, refresh_token: str) -> dict:
        payload = {
            "client_id": self._settings.gmail_client_id,
            "client_secret": self._settings.gmail_client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(GOOGLE_TOKEN_URL, data=payload)
            response.raise_for_status()
            return response.json()

    @staticmethod
    def encrypt_tokens(tokens: dict) -> str:
        return encrypt_session(json.dumps(tokens))

    @staticmethod
    def decrypt_tokens(encrypted: str) -> dict:
        return json.loads(decrypt_session(encrypted))

    async def get_access_token(self, encrypted_tokens: str) -> tuple[str, dict]:
        tokens = self.decrypt_tokens(encrypted_tokens)
        access = tokens.get("access_token")
        expires_at = tokens.get("expires_at", 0)
        if access and expires_at > datetime.now(tz=UTC).timestamp() + 60:
            return access, tokens

        refresh = tokens.get("refresh_token")
        if not refresh:
            raise ValueError("gmail_token_expired")

        refreshed = await self.refresh_access_token(refresh)
        tokens["access_token"] = refreshed["access_token"]
        tokens["expires_at"] = datetime.now(tz=UTC).timestamp() + int(refreshed.get("expires_in", 3600))
        if "refresh_token" in refreshed:
            tokens["refresh_token"] = refreshed["refresh_token"]
        return tokens["access_token"], tokens

    async def _fetch_gmail_profile_email(self, access_token: str) -> str:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{GMAIL_API}/profile",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            response.raise_for_status()
            return response.json().get("emailAddress", "")

    async def _fetch_userinfo_email(self, access_token: str) -> str:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                "https://www.googleapis.com/oauth2/v2/userinfo",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            response.raise_for_status()
            return response.json().get("email", "")

    async def resolve_account_email(self, access_token: str) -> str:
        for fetcher, label in (
            (self._fetch_userinfo_email, "userinfo"),
            (self._fetch_gmail_profile_email, "gmail_profile"),
        ):
            try:
                email = await fetcher(access_token)
                if email:
                    return email
            except httpx.HTTPStatusError as exc:
                logger.warning(
                    "gmail_email_lookup_failed",
                    source=label,
                    status=exc.response.status_code,
                    body=exc.response.text[:300],
                )
            except httpx.HTTPError as exc:
                logger.warning("gmail_email_lookup_failed", source=label, error=str(exc))
        return ""

    async def fetch_messages(
        self,
        encrypted_tokens: str,
        since: datetime,
        max_messages: int,
    ) -> tuple[list[ContentMessage], dict]:
        access_token, tokens = await self.get_access_token(encrypted_tokens)
        query = f"in:inbox after:{since.strftime('%Y/%m/%d')}"

        async with httpx.AsyncClient(timeout=60.0) as client:
            headers = {"Authorization": f"Bearer {access_token}"}
            list_resp = await client.get(
                f"{GMAIL_API}/messages",
                params={"q": query, "maxResults": max_messages},
                headers=headers,
            )
            if list_resp.status_code == 403:
                logger.error("gmail_api_forbidden", body=list_resp.text[:300])
                raise ValueError("gmail_api_disabled")
            list_resp.raise_for_status()
            ids = [item["id"] for item in list_resp.json().get("messages", [])]

            messages: list[ContentMessage] = []
            for msg_id in ids:
                msg_resp = await client.get(
                    f"{GMAIL_API}/messages/{msg_id}",
                    params={"format": "full"},
                    headers=headers,
                )
                if msg_resp.status_code != 200:
                    continue
                parsed = _parse_gmail_message(msg_resp.json())
                if parsed and parsed.date >= since:
                    messages.append(parsed)

        messages.sort(key=lambda m: m.date)
        logger.info("gmail_messages_fetched", count=len(messages), since=since.isoformat())
        return messages, tokens

    async def complete_oauth(self, code: str) -> tuple[dict, str]:
        raw = await self.exchange_code(code)
        expires_at = datetime.now(tz=UTC).timestamp() + int(raw.get("expires_in", 3600))
        tokens = {
            "access_token": raw["access_token"],
            "refresh_token": raw.get("refresh_token"),
            "expires_at": expires_at,
        }
        email = await self.resolve_account_email(tokens["access_token"])
        if not email:
            logger.warning("gmail_email_unresolved_tokens_saved")
        return tokens, email or "Gmail"


def gmail_message_url(message_id: str) -> str:
    return f"https://mail.google.com/mail/u/0/#inbox/{message_id}"


def _decode_body(data: str) -> str:
    padded = data + "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(padded.encode()).decode("utf-8", errors="replace")


def _headers_map(headers: list[dict]) -> dict[str, str]:
    return {h["name"].lower(): h["value"] for h in headers if "name" in h and "value" in h}


def _extract_plain_text(payload: dict) -> str:
    mime = payload.get("mimeType", "")
    body = payload.get("body", {})
    data = body.get("data")
    if data and mime == "text/plain":
        return _decode_body(data).strip()

    for part in payload.get("parts", []):
        text = _extract_plain_text(part)
        if text:
            return text
    if data and mime.startswith("text/"):
        return _decode_body(data).strip()
    return ""


def _parse_gmail_message(data: dict) -> ContentMessage | None:
    payload = data.get("payload") or {}
    headers = _headers_map(payload.get("headers", []))
    subject = headers.get("subject", "(no subject)")
    sender = headers.get("from", "unknown")
    _, email_addr = parseaddr(sender)
    body = _extract_plain_text(payload)
    if not body:
        body = data.get("snippet", "").strip()
    if not body:
        return None

    internal_date = int(data.get("internalDate", "0")) / 1000
    msg_date = datetime.fromtimestamp(internal_date, tz=UTC)
    msg_id = data.get("id", "")
    label = email_addr or sender
    text = f"Subject: {subject}\nFrom: {sender}\n\n{body}"
    return ContentMessage(
        text=text,
        source=f"email:{label}",
        date=msg_date,
        message_id=msg_id,
        post_url=gmail_message_url(msg_id),
    )
