from aiogram import Router

from app.bot.handlers import onboarding, platform, sources

router = Router(name="root")
router.include_router(onboarding.router)
router.include_router(platform.router)
router.include_router(sources.router)
