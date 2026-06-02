# AI Digest Bot

Telegram bot that sends **scheduled AI digests** from a curated list of public channels.

## User flow

1. **Welcome** + inline language choice (🇷🇺 / 🇬🇧)
2. **Channels** — multi-select from catalog (toggle + Continue)
3. **Frequency** — 12h / 1 day / 3 days / 1 week (digest period = delivery interval)
4. **Delivery time** — hour in `DEFAULT_TIMEZONE` (for 12h — twice daily)
5. **Done** — automatic digests on schedule + «Get now» button

All navigation uses **inline keyboards** (no slash commands required).

## Frequency logic

| Choice | Digest covers | Delivered |
|--------|---------------|-----------|
| Every 12h | Last 12 hours | At chosen time + 12h later |
| Once a day | Last 24 hours | Daily at chosen time |
| Every 3 days | Last 3 days | Every 3 days at chosen time |
| Once a week | Last 7 days | Weekly at chosen time |

## Quick start

```bash
cp .env.example .env
# fill BOT_TOKEN, TELEGRAM_*, DATABASE_URL, AI settings
docker compose up --build
```

## Configuration

| Variable | Description |
|----------|-------------|
| `DEFAULT_TIMEZONE` | Timezone for delivery (e.g. `Europe/Moscow`) |
| `CATALOG_CHANNELS` | `@channel:Title,@channel2:Title2` |
| `BOT_PROXY_URL` | Proxy for Bot API if needed |

Default catalog (if `CATALOG_CHANNELS` empty): `@ai_news`, `@python`, `@openai`, `@durov`.

## Commands

- `/start` — welcome or main menu
- `/menu` — main menu

## Architecture

```text
app/
  bot/handlers/onboarding.py  # full UX flow
  models/catalog_channel.py   # channel catalog
  services/frequency.py       # 12h / 1d / 3d / 1w
  services/schedule_service.py
  workers/scheduler.py        # minute tick, auto delivery
  i18n/                       # ru (default) + en
```

## Note on database

Schema changed (catalog + user schedule). For a clean start:

```bash
docker compose down -v
docker compose up --build
```
