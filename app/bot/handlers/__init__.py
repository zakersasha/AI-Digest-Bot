from aiogram import Router

from app.bot.handlers import add, digest, sources, start

router = Router(name="root")
router.include_router(start.router)
router.include_router(add.router)
router.include_router(sources.router)
router.include_router(digest.router)
