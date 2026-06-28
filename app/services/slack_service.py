import json
from dataclasses import dataclass
from datetime import UTC, datetime
from urllib.parse import urlencode

import httpx

from app.config import Settings
from app.services.content_message import ContentMessage
from app.utils.crypto import decrypt_session, encrypt_session
from app.utils.logging import get_logger

logger = get_logger(__name__)

SLACK_API = "https://slack.com/api"
SLACK_USER_SCOPES = (
    "channels:read "
    "channels:history "
    "groups:read "
    "groups:history"
)
SLACK_AUTH_URL = "https://slack.com/oauth/v2/authorize"
_SKIP_SUBTYPES = frozenset(
    {
        "channel_join",
        "channel_leave",
        "group_join",
        "group_leave",
        "bot_add",
        "bot_remove",
        "channel_topic",
        "channel_purpose",
        "channel_name",
        "channel_archive",
        "channel_unarchive",
    }
)


@dataclass(frozen=True)
class SlackChannelInfo:
    channel_id: str
    name: str
    is_private: bool


class SlackService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def is_configured(self) -> bool:
        return bool(self._settings.slack_client_id and self._settings.slack_client_secret)

    def build_auth_url(self, state: str) -> str:
        params = {
            "client_id": self._settings.slack_client_id,
            "user_scope": SLACK_USER_SCOPES,
            "redirect_uri": self._settings.slack_redirect_uri,
            "state": state,
        }
        return f"{SLACK_AUTH_URL}?{urlencode(params)}"

    async def exchange_code(self, code: str) -> dict:
        payload = {
            "client_id": self._settings.slack_client_id,
            "client_secret": self._settings.slack_client_secret,
            "code": code,
            "redirect_uri": self._settings.slack_redirect_uri,
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(f"{SLACK_API}/oauth.v2.access", data=payload)
            response.raise_for_status()
            data = response.json()
        if not data.get("ok"):
            raise ValueError(data.get("error", "slack_oauth_failed"))
        return data

    @staticmethod
    def encrypt_tokens(tokens: dict) -> str:
        return encrypt_session(json.dumps(tokens))

    @staticmethod
    def decrypt_tokens(encrypted: str) -> dict:
        try:
            return json.loads(decrypt_session(encrypted))
        except ValueError as exc:
            if "Invalid encrypted session" in str(exc):
                raise ValueError("slack_token_invalid") from exc
            raise

    def get_user_access_token(self, encrypted_tokens: str) -> str:
        tokens = self.decrypt_tokens(encrypted_tokens)
        access = tokens.get("user_access_token")
        if not access:
            raise ValueError("slack_token_expired")
        return access

    async def _api_get(self, method: str, access_token: str, params: dict | None = None) -> dict:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.get(
                f"{SLACK_API}/{method}",
                headers={"Authorization": f"Bearer {access_token}"},
                params=params or {},
            )
            response.raise_for_status()
            data = response.json()
        if not data.get("ok"):
            error = data.get("error", "slack_api_error")
            if error in ("token_revoked", "invalid_auth", "not_authed"):
                raise ValueError("slack_token_expired")
            raise ValueError(error)
        return data

    async def list_channels(self, encrypted_tokens: str) -> list[SlackChannelInfo]:
        access_token = self.get_user_access_token(encrypted_tokens)
        channels: list[SlackChannelInfo] = []
        cursor: str | None = None

        while True:
            params: dict[str, str | int] = {
                "types": "public_channel,private_channel",
                "exclude_archived": "true",
                "limit": 200,
            }
            if cursor:
                params["cursor"] = cursor
            data = await self._api_get("conversations.list", access_token, params)
            for item in data.get("channels", []):
                is_private = bool(item.get("is_private"))
                is_member = bool(item.get("is_member"))
                if is_private and not is_member:
                    continue
                name = (item.get("name") or "").strip()
                channel_id = item.get("id")
                if not channel_id or not name:
                    continue
                channels.append(
                    SlackChannelInfo(
                        channel_id=channel_id,
                        name=name,
                        is_private=is_private,
                    )
                )
            cursor = (data.get("response_metadata") or {}).get("next_cursor") or ""
            if not cursor:
                break

        channels.sort(key=lambda c: c.name.lower())
        logger.info("slack_channels_listed", count=len(channels))
        return channels

    async def fetch_messages(
        self,
        encrypted_tokens: str,
        channel_id: str,
        channel_name: str,
        since: datetime,
        max_messages: int,
    ) -> list[ContentMessage]:
        access_token = self.get_user_access_token(encrypted_tokens)
        oldest = str(since.timestamp())
        messages: list[ContentMessage] = []

        data = await self._api_get(
            "conversations.history",
            access_token,
            {"channel": channel_id, "oldest": oldest, "limit": min(max_messages, 100)},
        )
        for item in data.get("messages", []):
            parsed = _parse_slack_message(item, channel_id, channel_name)
            if parsed and parsed.date >= since:
                messages.append(parsed)

        messages.sort(key=lambda m: m.date)
        logger.info(
            "slack_messages_fetched",
            channel=channel_name,
            count=len(messages),
            since=since.isoformat(),
        )
        return messages

    async def complete_oauth(self, code: str) -> tuple[dict, str]:
        raw = await self.exchange_code(code)
        authed_user = raw.get("authed_user") or {}
        user_token = authed_user.get("access_token")
        if not user_token:
            raise ValueError("slack_no_user_token")

        team = raw.get("team") or {}
        tokens = {
            "user_access_token": user_token,
            "team_id": team.get("id", ""),
            "team_name": team.get("name", ""),
            "user_id": authed_user.get("id", ""),
        }
        team_name = team.get("name") or "Slack"
        return tokens, team_name


def slack_message_url(channel_id: str, ts: str) -> str:
    ts_compact = ts.replace(".", "")
    return f"https://slack.com/archives/{channel_id}/p{ts_compact}"


def _parse_slack_message(data: dict, channel_id: str, channel_name: str) -> ContentMessage | None:
    subtype = data.get("subtype")
    if subtype in _SKIP_SUBTYPES:
        return None
    if data.get("hidden"):
        return None

    text = (data.get("text") or "").strip()
    if not text:
        return None
    if subtype == "bot_message" and len(text) < 20:
        return None

    ts = data.get("ts")
    if not ts:
        return None

    msg_date = datetime.fromtimestamp(float(ts), tz=UTC)
    user_name = data.get("username") or data.get("user") or "user"
    label = f"#{channel_name}"
    body = f"{user_name}: {text}" if subtype != "bot_message" else text
    return ContentMessage(
        text=body,
        source=f"slack:{label}",
        date=msg_date,
        message_id=ts,
        post_url=slack_message_url(channel_id, ts),
    )
