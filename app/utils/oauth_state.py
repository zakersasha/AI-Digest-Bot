"""Signed OAuth state — survives bot restarts, no in-memory store."""

import base64
import hashlib
import hmac
import json
import time


def _b64_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


def _b64_decode(data: str) -> bytes:
    padded = data + "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(padded.encode())


def create_signed_oauth_state(telegram_id: int, secret: str, *, ttl_seconds: int = 900) -> str:
    payload = {"tg": telegram_id, "exp": int(time.time()) + ttl_seconds}
    body = _b64_encode(json.dumps(payload, separators=(",", ":")).encode())
    sig = hmac.new(secret.encode(), body.encode(), hashlib.sha256).hexdigest()[:20]
    return f"{body}.{sig}"


def verify_signed_oauth_state(state: str, secret: str) -> int | None:
    if not state or "." not in state:
        return None
    body, sig = state.rsplit(".", 1)
    expected = hmac.new(secret.encode(), body.encode(), hashlib.sha256).hexdigest()[:20]
    if not hmac.compare_digest(sig, expected):
        return None
    try:
        payload = json.loads(_b64_decode(body))
        telegram_id = int(payload["tg"])
        if int(payload.get("exp", 0)) < time.time():
            return None
        return telegram_id
    except (ValueError, KeyError, json.JSONDecodeError):
        return None


def create_oauth_state(telegram_id: int) -> str:
    from app.config import get_settings

    settings = get_settings()
    secret = settings.session_encryption_key or settings.bot_token
    return create_signed_oauth_state(telegram_id, secret)
