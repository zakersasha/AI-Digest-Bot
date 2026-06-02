from aiogram import Router

from app.bot.handlers import onboarding

router = Router(name="root")
router.include_router(onboarding.router)
