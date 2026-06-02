from aiogram import Router

from app.bot.handlers import login, onboarding

router = Router(name="root")
router.include_router(login.router)
router.include_router(onboarding.router)
