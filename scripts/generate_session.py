"""Generate Telethon session string for TELEGRAM_SESSION_STRING env var."""

import socks
from telethon.sync import TelegramClient
from telethon.sessions import StringSession

# 1. Ваши данные из my.telegram.org
api_id = 1
api_hash = '1'

# 2. Настройки вашего HTTPS-прокси
PROXY_IP = '1'   # IP-адрес прокси
PROXY_PORT = 1           # Порт прокси
PROXY_USER = '1'     # Логин (если прокси без авторизации, поставьте None)
PROXY_PASS = '1'     # Пароль (если прокси без авторизации, поставьте None)

# Формируем конфигурацию прокси (для HTTPS используется socks.HTTP)
proxy_config = (socks.HTTP, PROXY_IP, PROXY_PORT, True, PROXY_USER, PROXY_PASS)

print("Подключение к Telegram через HTTPS-прокси...")

try:
    with TelegramClient(StringSession(), api_id, api_hash, proxy=proxy_config) as client:
        print("\nУспешное подключение!")
        print("\nВаша строка сессии (TELEGRAM_SESSION_STRING):\n")
        print(client.session.save())
        print("\nСкопируйте строку выше. Никому её не показывайте!")
except Exception as e:
    print(f"\nПроизошла ошибка: {e}")
    print("Проверьте, работает ли ваш прокси и поддерживает ли он HTTPS-соединения.")
