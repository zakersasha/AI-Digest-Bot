import secrets
from collections.abc import Awaitable, Callable

from aiohttp import web

from app.db.session import async_session_factory
from app.repositories.user_repository import UserRepository
from app.services.gmail_service import GmailService
from app.utils.logging import get_logger

logger = get_logger(__name__)

_pending_states: dict[str, int] = {}


def create_oauth_state(telegram_id: int) -> str:
    state = secrets.token_urlsafe(24)
    _pending_states[state] = telegram_id
    return state


def pop_oauth_telegram_id(state: str) -> int | None:
    return _pending_states.pop(state, None)


async def gmail_oauth_callback(request: web.Request) -> web.Response:
    settings = request.app["settings"]
    gmail = GmailService(settings)

    state = request.query.get("state", "")
    code = request.query.get("code", "")
    error = request.query.get("error")

    if error:
        return web.Response(text=f"Gmail authorization failed: {error}", status=400)

    telegram_id = pop_oauth_telegram_id(state)
    if not telegram_id or not code:
        return web.Response(text="Invalid or expired OAuth state.", status=400)

    try:
        tokens, email = await gmail.complete_oauth(code)
        async with async_session_factory() as session:
            repo = UserRepository(session)
            await repo.save_gmail_tokens(telegram_id, tokens, email)
            await repo.set_content_platform(telegram_id, "gmail")
            await session.commit()
    except Exception:
        logger.exception("gmail_oauth_callback_failed", telegram_id=telegram_id)
        return web.Response(text="Failed to save Gmail tokens.", status=500)

    logger.info("gmail_oauth_success", telegram_id=telegram_id, email=email)
    return web.Response(
        text="Gmail connected successfully. Return to the Telegram bot.",
        content_type="text/html",
    )


def create_oauth_app(settings) -> web.Application:
    app = web.Application()
    app["settings"] = settings
    app.router.add_get("/oauth/gmail/callback", gmail_oauth_callback)
    return app


async def start_oauth_server(
    settings,
    *,
    on_startup: Callable[[], Awaitable[None]] | None = None,
) -> web.AppRunner:
    app = create_oauth_app(settings)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, settings.gmail_oauth_host, settings.gmail_oauth_port)
    await site.start()
    if on_startup:
        await on_startup()
    logger.info(
        "gmail_oauth_server_started",
        host=settings.gmail_oauth_host,
        port=settings.gmail_oauth_port,
    )
    return runner
