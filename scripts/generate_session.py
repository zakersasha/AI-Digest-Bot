"""Generate Telethon session string for TELEGRAM_SESSION_STRING env var."""

import asyncio
import os

from telethon import TelegramClient
from telethon.sessions import StringSession


async def main() -> None:
    api_id = int(os.environ["TELEGRAM_API_ID"])
    api_hash = os.environ["TELEGRAM_API_HASH"]

    client = TelegramClient(StringSession(), api_id, api_hash)
    await client.start()
    session_string = client.session.save()
    print("\nAdd this to your .env:\n")
    print(f"TELEGRAM_SESSION_STRING={session_string}\n")
    await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
