import base64
import json
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from urllib.parse import urlencode

import httpx

from app.config import Settings, effective_linkedin_proxy_url
from app.models.linkedin_profile import LinkedInProfile
from app.services.content_message import ContentMessage
from app.utils.crypto import decrypt_session, encrypt_session
from app.utils.http_proxy import create_httpx_client, proxy_host
from app.utils.logging import get_logger

logger = get_logger(__name__)

LINKEDIN_AUTH_URL = "https://www.linkedin.com/oauth/v2/authorization"
LINKEDIN_TOKEN_URL = "https://www.linkedin.com/oauth/v2/accessToken"
LINKEDIN_USERINFO_URL = "https://api.linkedin.com/v2/userinfo"
LINKEDIN_API = "https://api.linkedin.com"
LINKEDIN_VERSIONS = ("202502", "202401", "202305")

LINKEDIN_OIDC_SCOPES = ("openid", "profile", "email")


@dataclass(frozen=True)
class FollowedProfile:
    slug: str
    profile_type: str
    title: str
    url: str
    linkedin_urn: str | None = None


class LinkedInService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._proxy_url = effective_linkedin_proxy_url(settings)

    def _client(self, *, timeout: float = 30.0) -> httpx.AsyncClient:
        return create_httpx_client(self._proxy_url, timeout)

    @staticmethod
    def _decode_jwt_payload(token: str) -> dict:
        try:
            parts = token.split(".")
            if len(parts) < 2:
                return {}
            payload = parts[1]
            padding = "=" * (-len(payload) % 4)
            raw = base64.urlsafe_b64decode(payload + padding)
            return json.loads(raw)
        except Exception:
            return {}

    def is_configured(self) -> bool:
        return bool(self._settings.linkedin_client_id and self._settings.linkedin_client_secret)

    def oauth_scopes(self) -> str:
        extra = (self._settings.linkedin_extra_scopes or "").strip()
        scopes = list(LINKEDIN_OIDC_SCOPES)
        if extra:
            for part in extra.split():
                if part and part not in scopes:
                    scopes.append(part)
        return " ".join(scopes)

    def build_auth_url(self, state: str) -> str:
        params = {
            "response_type": "code",
            "client_id": self._settings.linkedin_client_id,
            "redirect_uri": self._settings.linkedin_redirect_uri,
            "state": state,
            "scope": self.oauth_scopes(),
        }
        return f"{LINKEDIN_AUTH_URL}?{urlencode(params)}"

    async def exchange_code(self, code: str) -> dict:
        payload = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": self._settings.linkedin_redirect_uri,
            "client_id": self._settings.linkedin_client_id,
            "client_secret": self._settings.linkedin_client_secret,
        }
        async with self._client() as client:
            response = await client.post(LINKEDIN_TOKEN_URL, data=payload)
            response.raise_for_status()
            data = response.json()
        data["expires_at"] = int(time.time()) + int(data.get("expires_in", 3600))
        return data

    @staticmethod
    def encrypt_tokens(tokens: dict) -> str:
        return encrypt_session(json.dumps(tokens))

    @staticmethod
    def decrypt_tokens(encrypted: str) -> dict:
        return json.loads(decrypt_session(encrypted))

    def _headers(self, access_token: str, *, version: str = LINKEDIN_VERSIONS[0]) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {access_token}",
            "LinkedIn-Version": version,
            "X-Restli-Protocol-Version": "2.0.0",
        }

    @staticmethod
    def _extract_post_text(item: dict) -> str:
        commentary = item.get("commentary")
        if isinstance(commentary, str) and commentary.strip():
            return commentary.strip()
        if isinstance(commentary, dict):
            text = commentary.get("text") or ""
            if str(text).strip():
                return str(text).strip()

        content = item.get("content")
        if isinstance(content, dict):
            for key in ("title", "description"):
                value = content.get(key)
                if isinstance(value, str) and value.strip():
                    return value.strip()
            for nested in ("article", "media", "multiImage"):
                block = content.get(nested)
                if isinstance(block, dict):
                    for key in ("title", "description"):
                        value = block.get(key)
                        if isinstance(value, str) and value.strip():
                            return value.strip()

        text_field = item.get("text")
        if isinstance(text_field, dict):
            return str(text_field.get("text") or "").strip()
        if isinstance(text_field, str):
            return text_field.strip()
        return ""

    @staticmethod
    def _post_timestamp(item: dict) -> int:
        for key in ("createdAt", "lastModifiedAt", "publishedAt", "created", "lastModified"):
            value = item.get(key)
            if value:
                return int(value)
        return 0

    @staticmethod
    def _post_id(item: dict) -> str:
        for key in ("id", "urn", "activity"):
            value = item.get(key)
            if value:
                return str(value)
        return ""

    async def get_access_token(self, encrypted_tokens: str) -> tuple[str, dict]:
        tokens = self.decrypt_tokens(encrypted_tokens)
        access = tokens.get("access_token")
        expires_at = tokens.get("expires_at", 0)
        if access and int(expires_at) > int(time.time()) + 60:
            return access, tokens

        refresh = tokens.get("refresh_token")
        if not refresh:
            raise ValueError("linkedin_token_expired")

        payload = {
            "grant_type": "refresh_token",
            "refresh_token": refresh,
            "client_id": self._settings.linkedin_client_id,
            "client_secret": self._settings.linkedin_client_secret,
        }
        async with self._client() as client:
            response = await client.post(LINKEDIN_TOKEN_URL, data=payload)
            response.raise_for_status()
            refreshed = response.json()
        tokens["access_token"] = refreshed["access_token"]
        tokens["expires_at"] = int(time.time()) + int(refreshed.get("expires_in", 3600))
        if refreshed.get("refresh_token"):
            tokens["refresh_token"] = refreshed["refresh_token"]
        return tokens["access_token"], tokens

    async def fetch_member_info(self, access_token: str) -> dict:
        headers = {"Authorization": f"Bearer {access_token}"}
        async with self._client() as client:
            response = await client.get(LINKEDIN_USERINFO_URL, headers=headers)
            response.raise_for_status()
            return response.json()

    async def resolve_member_info(self, tokens: dict) -> dict:
        id_token = tokens.get("id_token")
        if id_token:
            claims = self._decode_jwt_payload(id_token)
            if claims.get("sub"):
                logger.info("linkedin_member_info_from_id_token")
                return claims

        access = tokens.get("access_token")
        if not access:
            raise ValueError("linkedin_no_token")

        try:
            return await self.fetch_member_info(access)
        except httpx.HTTPError as exc:
            logger.warning(
                "linkedin_userinfo_failed",
                error=str(exc),
                proxy=proxy_host(self._proxy_url) if self._proxy_url else None,
            )
            if id_token:
                claims = self._decode_jwt_payload(id_token)
                if claims.get("sub"):
                    return claims
            raise

    async def fetch_followed_profiles(self, encrypted_tokens: str) -> list[FollowedProfile]:
        access_token, _ = await self.get_access_token(encrypted_tokens)
        profiles: list[FollowedProfile] = []
        seen: set[str] = set()

        async with self._client() as client:
            try:
                response = await client.get(
                    f"{LINKEDIN_API}/rest/memberFollowedOrganizations",
                    params={"q": "member", "count": 50},
                    headers=self._headers(access_token),
                )
                if response.status_code == 200:
                    for element in response.json().get("elements", []):
                        org = element.get("organization") or element.get("organizationalTarget")
                        if not org:
                            continue
                        urn = org if isinstance(org, str) else org.get("id") or org.get("urn")
                        vanity = element.get("vanityName") or element.get("localizedName") or ""
                        name = element.get("name") or vanity or "Company"
                        slug = (vanity or name).lower().replace(" ", "-")[:64]
                        if not slug or slug in seen:
                            continue
                        seen.add(slug)
                        profiles.append(
                            FollowedProfile(
                                slug=slug,
                                profile_type="company",
                                title=str(name),
                                url=f"https://www.linkedin.com/company/{slug}",
                                linkedin_urn=urn if isinstance(urn, str) else str(urn) if urn else None,
                            )
                        )
            except httpx.HTTPError as exc:
                logger.warning("linkedin_followed_orgs_failed", error=str(exc))

            try:
                response = await client.get(
                    f"{LINKEDIN_API}/v2/organizationalEntityFollows",
                    params={"q": "member"},
                    headers=self._headers(access_token),
                )
                if response.status_code == 200:
                    for element in response.json().get("elements", []):
                        org = element.get("organizationalTarget", "")
                        slug = str(org).split(":")[-1] if org else ""
                        if not slug or slug in seen:
                            continue
                        seen.add(slug)
                        profiles.append(
                            FollowedProfile(
                                slug=slug,
                                profile_type="company",
                                title=slug,
                                url=f"https://www.linkedin.com/company/{slug}",
                                linkedin_urn=str(org) if org else None,
                            )
                        )
            except httpx.HTTPError as exc:
                logger.warning("linkedin_entity_follows_failed", error=str(exc))

        profiles.sort(key=lambda item: item.title.lower())
        logger.info("linkedin_followed_fetched", count=len(profiles))
        return profiles

    async def _resolve_author_urn(
        self,
        client: httpx.AsyncClient,
        access_token: str,
        profile: LinkedInProfile,
    ) -> str | None:
        if profile.linkedin_urn:
            urn = profile.linkedin_urn
            if urn.startswith("urn:"):
                return urn
            return f"urn:li:organization:{urn}"

        if profile.profile_type != "company":
            logger.warning("linkedin_person_profile_no_urn", slug=profile.profile_slug)
            return None

        for version in LINKEDIN_VERSIONS:
            headers = self._headers(access_token, version=version)
            for path, params in (
                (f"{LINKEDIN_API}/rest/organizations", {"q": "vanityName", "vanityName": profile.profile_slug}),
                (f"{LINKEDIN_API}/v2/organizations", {"q": "vanityName", "vanityName": profile.profile_slug}),
            ):
                try:
                    response = await client.get(path, params=params, headers=headers)
                    if response.status_code != 200:
                        continue
                    elements = response.json().get("elements", [])
                    if not elements:
                        continue
                    org_id = elements[0].get("id")
                    if org_id:
                        return f"urn:li:organization:{org_id}"
                except httpx.HTTPError:
                    continue
        return None

    def _parse_post_elements(
        self,
        elements: list,
        profile: LinkedInProfile,
        since_ts: int,
    ) -> list[ContentMessage]:
        messages: list[ContentMessage] = []
        label = profile.title or profile.profile_slug
        for item in elements:
            created = self._post_timestamp(item)
            if created and created < since_ts:
                continue
            text = self._extract_post_text(item)
            if not text:
                continue
            post_id = self._post_id(item)
            post_url = profile.profile_url
            if post_id:
                post_url = f"https://www.linkedin.com/feed/update/{post_id}"
            messages.append(
                ContentMessage(
                    text=text[:2000],
                    source=f"linkedin:{label}",
                    date=datetime.fromtimestamp(created / 1000, tz=UTC) if created else datetime.now(tz=UTC),
                    message_id=str(post_id or f"{profile.profile_slug}:{created}"),
                    post_url=post_url,
                )
            )
        return messages

    async def _fetch_posts_rest(
        self,
        client: httpx.AsyncClient,
        access_token: str,
        author_urn: str,
        profile: LinkedInProfile,
        since_ts: int,
    ) -> tuple[list[ContentMessage], str | None]:
        author_variants = (author_urn, f"List({author_urn})")
        last_error: str | None = None

        for version in LINKEDIN_VERSIONS:
            headers = self._headers(access_token, version=version)
            for author_value in author_variants:
                try:
                    response = await client.get(
                        f"{LINKEDIN_API}/rest/posts",
                        params={
                            "q": "author",
                            "author": author_value,
                            "count": self._settings.linkedin_max_posts,
                            "sortBy": "LAST_MODIFIED",
                        },
                        headers=headers,
                    )
                except httpx.HTTPError as exc:
                    last_error = str(exc)
                    continue

                if response.status_code != 200:
                    body = response.text[:300]
                    last_error = f"HTTP {response.status_code}: {body}"
                    logger.warning(
                        "linkedin_posts_failed",
                        slug=profile.profile_slug,
                        status=response.status_code,
                        version=version,
                        author=author_value,
                        body=body,
                    )
                    continue

                messages = self._parse_post_elements(
                    response.json().get("elements", []),
                    profile,
                    since_ts,
                )
                if messages:
                    return messages, None
                last_error = "empty_elements"

        return [], last_error

    async def _fetch_posts_ugc(
        self,
        client: httpx.AsyncClient,
        access_token: str,
        author_urn: str,
        profile: LinkedInProfile,
        since_ts: int,
    ) -> tuple[list[ContentMessage], str | None]:
        headers = self._headers(access_token)
        try:
            response = await client.get(
                f"{LINKEDIN_API}/v2/ugcPosts",
                params={
                    "q": "authors",
                    "authors": f"List({author_urn})",
                    "count": self._settings.linkedin_max_posts,
                },
                headers=headers,
            )
        except httpx.HTTPError as exc:
            return [], str(exc)

        if response.status_code != 200:
            body = response.text[:300]
            logger.warning(
                "linkedin_ugc_posts_failed",
                slug=profile.profile_slug,
                status=response.status_code,
                body=body,
            )
            return [], f"HTTP {response.status_code}: {body}"

        elements = response.json().get("elements", [])
        messages: list[ContentMessage] = []
        label = profile.title or profile.profile_slug
        for item in elements:
            created = self._post_timestamp(item)
            if created and created < since_ts:
                continue
            text = self._extract_post_text(item)
            if not text:
                specific = item.get("specificContent", {}).get("com.linkedin.ugc.ShareContent", {})
                if isinstance(specific, dict):
                    share_text = specific.get("shareCommentary", {}).get("text")
                    if isinstance(share_text, str):
                        text = share_text.strip()
            if not text:
                continue
            post_id = self._post_id(item)
            post_url = profile.profile_url
            if post_id:
                post_url = f"https://www.linkedin.com/feed/update/{post_id}"
            messages.append(
                ContentMessage(
                    text=text[:2000],
                    source=f"linkedin:{label}",
                    date=datetime.fromtimestamp(created / 1000, tz=UTC) if created else datetime.now(tz=UTC),
                    message_id=str(post_id or f"{profile.profile_slug}:{created}"),
                    post_url=post_url,
                )
            )
        return messages, None if messages else "empty_ugc"

    async def fetch_posts(
        self,
        encrypted_tokens: str,
        profile: LinkedInProfile,
        since: datetime,
    ) -> tuple[list[ContentMessage], dict, str | None]:
        access_token, tokens = await self.get_access_token(encrypted_tokens)
        since_ts = int(since.timestamp() * 1000)

        async with self._client() as client:
            author_urn = await self._resolve_author_urn(client, access_token, profile)
            if not author_urn:
                return [], tokens, "author_unresolved"

            messages, error = await self._fetch_posts_rest(
                client, access_token, author_urn, profile, since_ts
            )
            if messages:
                return messages, tokens, None

            messages, ugc_error = await self._fetch_posts_ugc(
                client, access_token, author_urn, profile, since_ts
            )
            if messages:
                return messages, tokens, None

            return [], tokens, ugc_error or error or "no_posts"
