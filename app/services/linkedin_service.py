import json
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from urllib.parse import urlencode

import httpx

from app.config import Settings
from app.models.linkedin_profile import LinkedInProfile
from app.services.content_message import ContentMessage
from app.utils.crypto import decrypt_session, encrypt_session
from app.utils.logging import get_logger

logger = get_logger(__name__)

LINKEDIN_AUTH_URL = "https://www.linkedin.com/oauth/v2/authorization"
LINKEDIN_TOKEN_URL = "https://www.linkedin.com/oauth/v2/accessToken"
LINKEDIN_USERINFO_URL = "https://api.linkedin.com/v2/userinfo"
LINKEDIN_API = "https://api.linkedin.com"
LINKEDIN_VERSION = "202401"

LINKEDIN_SCOPES = "openid profile email r_organization_follows r_organization_social"


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

    def is_configured(self) -> bool:
        return bool(self._settings.linkedin_client_id and self._settings.linkedin_client_secret)

    def build_auth_url(self, state: str) -> str:
        params = {
            "response_type": "code",
            "client_id": self._settings.linkedin_client_id,
            "redirect_uri": self._settings.linkedin_redirect_uri,
            "state": state,
            "scope": LINKEDIN_SCOPES,
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
        async with httpx.AsyncClient(timeout=30.0) as client:
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
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(LINKEDIN_TOKEN_URL, data=payload)
            response.raise_for_status()
            refreshed = response.json()
        tokens["access_token"] = refreshed["access_token"]
        tokens["expires_at"] = int(time.time()) + int(refreshed.get("expires_in", 3600))
        if refreshed.get("refresh_token"):
            tokens["refresh_token"] = refreshed["refresh_token"]
        return tokens["access_token"], tokens

    def _headers(self, access_token: str) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {access_token}",
            "LinkedIn-Version": LINKEDIN_VERSION,
            "X-Restli-Protocol-Version": "2.0.0",
        }

    async def fetch_member_info(self, access_token: str) -> dict:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(LINKEDIN_USERINFO_URL, headers=self._headers(access_token))
            response.raise_for_status()
            return response.json()

    async def fetch_followed_profiles(self, encrypted_tokens: str) -> list[FollowedProfile]:
        access_token, _ = await self.get_access_token(encrypted_tokens)
        profiles: list[FollowedProfile] = []
        seen: set[str] = set()

        async with httpx.AsyncClient(timeout=30.0) as client:
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
                                linkedin_urn=urn,
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
            return profile.linkedin_urn
        if profile.profile_type == "company":
            response = await client.get(
                f"{LINKEDIN_API}/v2/organizations",
                params={"q": "vanityName", "vanityName": profile.profile_slug},
                headers=self._headers(access_token),
            )
            if response.status_code == 200:
                elements = response.json().get("elements", [])
                if elements:
                    org_id = elements[0].get("id")
                    return f"urn:li:organization:{org_id}"
        return None

    async def fetch_posts(
        self,
        encrypted_tokens: str,
        profile: LinkedInProfile,
        since: datetime,
    ) -> list[ContentMessage]:
        access_token, _ = await self.get_access_token(encrypted_tokens)
        messages: list[ContentMessage] = []
        since_ts = int(since.timestamp() * 1000)

        async with httpx.AsyncClient(timeout=30.0) as client:
            author_urn = await self._resolve_author_urn(client, access_token, profile)
            if not author_urn:
                logger.warning("linkedin_author_unresolved", slug=profile.profile_slug)
                return messages

            try:
                response = await client.get(
                    f"{LINKEDIN_API}/rest/posts",
                    params={
                        "q": "author",
                        "author": author_urn,
                        "count": self._settings.linkedin_max_posts,
                        "sortBy": "LAST_MODIFIED",
                    },
                    headers=self._headers(access_token),
                )
                if response.status_code != 200:
                    logger.warning(
                        "linkedin_posts_failed",
                        slug=profile.profile_slug,
                        status=response.status_code,
                    )
                    return messages

                for item in response.json().get("elements", []):
                    created = item.get("createdAt") or item.get("lastModifiedAt") or 0
                    if created < since_ts:
                        continue
                    text = (
                        item.get("commentary")
                        or item.get("text", {}).get("text")
                        or item.get("content", {}).get("title", "")
                    )
                    if not text or not str(text).strip():
                        continue
                    post_id = item.get("id", "")
                    post_url = profile.profile_url
                    if post_id:
                        post_url = f"https://www.linkedin.com/feed/update/{post_id}"
                    label = profile.title or profile.profile_slug
                    msg_id = str(post_id or f"{profile.profile_slug}:{created}")
                    messages.append(
                        ContentMessage(
                            text=str(text).strip()[:2000],
                            source=f"linkedin:{label}",
                            date=datetime.fromtimestamp(created / 1000, tz=UTC),
                            message_id=msg_id,
                            post_url=post_url,
                        )
                    )
            except httpx.HTTPError as exc:
                logger.warning("linkedin_posts_error", slug=profile.profile_slug, error=str(exc))

        return messages
