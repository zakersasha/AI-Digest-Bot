from sqlalchemy.ext.asyncio import AsyncSession

from app.i18n.strings import STRINGS
from app.repositories.user_repository import UserRepository

DEFAULT_LANG = "en"
SUPPORTED_LANGS = ("ru", "en")


def t(lang: str | None, key: str, **kwargs: str) -> str:
    code = lang if lang in SUPPORTED_LANGS else DEFAULT_LANG
    template = STRINGS[code].get(key) or STRINGS[DEFAULT_LANG][key]
    return template.format(**kwargs) if kwargs else template


def language_name(lang: str) -> str:
    return "Russian" if lang == "ru" else "English"


def frequency_label(lang: str, code: str) -> str:
    return t(lang, f"freq_label_{code}")


def digest_title(lang: str, frequency: str, *, platform: str = "telegram") -> str:
    period = t(lang, f"digest_period_{frequency}")
    key = "digest_header_gmail" if platform == "gmail" else "digest_header"
    return t(lang, key, period=period)


async def resolve_lang(session: AsyncSession, telegram_id: int) -> str:
    repo = UserRepository(session)
    user = await repo.get_by_telegram_id(telegram_id)
    if user and user.language:
        return user.language
    return DEFAULT_LANG
