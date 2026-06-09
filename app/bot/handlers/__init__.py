from aiogram import Router

from app.bot.handlers import linkedin_auth, onboarding, platform, platforms_menu, sources, telethon_auth

router = Router(name="root")
router.include_router(onboarding.router)
router.include_router(platforms_menu.router)
router.include_router(platform.router)
router.include_router(sources.router)
router.include_router(telethon_auth.router)
router.include_router(linkedin_auth.router)
