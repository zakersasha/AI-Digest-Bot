import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken

from app.config import get_settings


def _fernet_key_material(secret: str) -> bytes:
    """Accept a Fernet key or derive one from any non-empty passphrase."""
    raw = secret.strip()
    try:
        Fernet(raw.encode())
        return raw.encode()
    except (ValueError, TypeError):
        pass
    return base64.urlsafe_b64encode(hashlib.sha256(raw.encode()).digest())


def _fernet() -> Fernet:
    key = get_settings().session_encryption_key
    if not key or not key.strip():
        raise RuntimeError("SESSION_ENCRYPTION_KEY is not configured")
    return Fernet(_fernet_key_material(key))


def encrypt_session(session_string: str) -> str:
    return _fernet().encrypt(session_string.encode()).decode()


def decrypt_session(encrypted: str) -> str:
    try:
        return _fernet().decrypt(encrypted.encode()).decode()
    except InvalidToken as exc:
        raise ValueError("Invalid encrypted session") from exc
