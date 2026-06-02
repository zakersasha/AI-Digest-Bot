# AI Digest Bot

Telegram bot that generates AI-powered digests from **public** Telegram channels and groups. Cut through information overload and get concise insights for the time window you care about.

## Features

- Add public channels/groups by `@username` or `t.me` link
- Toggle active sources and remove them inline
- Generate digests for **1h / 3h / 6h / 12h** windows
- AI scoring + summarization with swappable providers:
  - **Local** (default) — vLLM OpenAI-compatible API
  - **OpenAI** — proxy-compatible via `OPENAI_BASE_URL`
- PostgreSQL persistence (users, sources, digests)
- Docker Compose deployment

## Architecture

```text
app/
  ai/              # Provider abstraction (local / OpenAI)
  bot/             # aiogram handlers, keyboards, middlewares
  db/              # SQLAlchemy async engine
  models/          # User, Source, Digest
  repositories/    # Data access layer
  services/        # Telethon, digest, source logic
  utils/           # Logging
  workers/         # Placeholder for future job queue
```

## Prerequisites

1. **Bot token** — create via [@BotFather](https://t.me/BotFather)
2. **Telegram API credentials** — from [my.telegram.org](https://my.telegram.org)
3. **Telethon session** — user session required to read public channels
4. **PostgreSQL** — included in Docker Compose
5. **AI provider** — local vLLM endpoint or OpenAI API key

## Quick start (Docker)

1. Copy environment file:

```bash
cp .env.example .env
```

2. Fill in `.env`:

```env
BOT_TOKEN=your_bot_token
TELEGRAM_API_ID=123456
TELEGRAM_API_HASH=your_api_hash
TELEGRAM_SESSION_STRING=your_session_string
AI_PROVIDER=local
```

3. Generate Telethon session (one-time, local):

```bash
pip install telethon
set TELEGRAM_API_ID=123456
set TELEGRAM_API_HASH=your_api_hash
python scripts/generate_session.py
```

On Linux/macOS use `export` instead of `set`.

4. Start everything:

```bash
docker compose up --build
```

## Local development

```bash
poetry install
cp .env.example .env
# edit .env — use localhost DATABASE_URL for local Postgres
poetry run python main.py
```

Local Postgres URL example:

```env
DATABASE_URL=postgresql+asyncpg://digest:digest@localhost:5432/digest_bot
```

## Bot commands

| Command   | Description                          |
|-----------|--------------------------------------|
| `/start`  | Welcome message and menu             |
| `/add`    | Add a public channel or group        |
| `/sources`| List, toggle, and remove sources     |
| `/digest` | Pick timeframe and generate digest   |
| `/help`   | Help text                            |

## User flow

1. `/start` — welcome
2. `/add` → send `@channel` or `https://t.me/channel`
3. `/sources` — manage active sources
4. `/digest` → choose **1h / 3h / 6h / 12h**
5. Receive formatted AI digest

Example output:

```text
🔥 AI Digest (Last 6h)

1. OpenAI released ...
2. New Python framework ...
3. Major crypto market movement ...

Key trends:
- AI tooling growth
- Increased GPU demand
```

## AI providers

Switch via `AI_PROVIDER` in `.env`:

```env
# Local vLLM (default)
AI_PROVIDER=local
LOCAL_AI_BASE_URL=http://178.170.249.108:40000
LOCAL_AI_MODEL=openai/gpt-oss-20b

# OpenAI (proxy-compatible)
AI_PROVIDER=openai
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4.1-mini
OPENAI_BASE_URL=https://your-proxy/v1
```

## Configuration

| Variable                  | Description                              |
|---------------------------|------------------------------------------|
| `BOT_TOKEN`               | Telegram bot token                       |
| `DATABASE_URL`            | Async PostgreSQL URL                     |
| `AI_PROVIDER`             | `local` or `openai`                      |
| `TELEGRAM_API_ID`         | Telethon API ID                          |
| `TELEGRAM_API_HASH`       | Telethon API hash                        |
| `TELEGRAM_SESSION_STRING` | Authorized Telethon session              |
| `BOT_PROXY_URL`           | HTTP proxy for Bot API (if Telegram is blocked) |
| `BOT_API_TIMEOUT`         | Bot API request timeout in seconds (default 60) |
| `MAX_MESSAGES_PER_SOURCE` | Max messages fetched per source (default 30) |
| `MIN_IMPORTANCE_SCORE`    | Min AI score to include in digest (default 5) |

## Limitations (MVP)

- **Public channels/groups only** — no private chats or invite links
- Telethon user session required (Bot API alone cannot read channel history)
- Per-message AI scoring — capped by `MAX_MESSAGES_PER_SOURCE` for performance
- No Celery/Redis queue — digest runs inline with async AI calls

## Optional Redis

Redis is included as an optional profile for future use:

```bash
docker compose --profile optional up --build
```

## License

MIT
