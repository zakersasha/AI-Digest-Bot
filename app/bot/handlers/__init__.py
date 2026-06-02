from aiogram import Router

from app.bot.handlers import onboarding, sources

router = Router(name="root")
router.include_router(sources.router)
router.include_router(onboarding.router)
