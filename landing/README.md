# Briefly landing — brieflybot.pro

Лендинг + Privacy Policy + Terms of Service для Google OAuth.

## URL для Google Cloud Console

| Документ | URL |
|----------|-----|
| Privacy Policy | `https://brieflybot.pro/privacy-policy` |
| Terms of Service | `https://brieflybot.pro/terms-of-service` |
| Homepage | `https://brieflybot.pro/` |
| Gmail OAuth redirect | `https://brieflybot.pro/oauth/gmail/callback` |

---

## Ваш сервер: nginx в Docker (`~/cv_portfolio/nginx`)

У вас **нет** `/etc/nginx` на хосте. Nginx живёт в проекте `cv_portfolio`:

```
~/cv_portfolio/nginx/nginx.conf
~/cv_portfolio/nginx/conf.d/        ← сюда кладём brieflybot.pro.conf
```

Статика лендинга:

```
~/AI-Digest-Bot/landing/www/        ← index.html + docs/
~/AI-Digest-Bot/landing/certbot/      ← ACME challenge для Let's Encrypt
```

### Шаг 1 — DNS

A-запись `brieflybot.pro` → `37.230.114.25` (ваш IP).

### Шаг 2 — Volumes в docker-compose cv_portfolio

Откройте `~/cv_portfolio/docker-compose.yml`, в сервис **nginx** добавьте (см. `landing/cv_portfolio.volumes.example.txt`):

```yaml
extra_hosts:
  - "host.docker.internal:host-gateway"

volumes:
  - /root/AI-Digest-Bot/landing/www:/var/www/brieflybot.pro:ro
  - /root/AI-Digest-Bot/landing/certbot:/var/www/certbot:ro
  - /etc/letsencrypt:/etc/letsencrypt:ro
```

Перезапустите nginx:

```bash
cd ~/cv_portfolio
docker compose up -d nginx
```

### Шаг 3 — Деплой (на сервере, не с Windows)

На сервере уже есть `~/AI-Digest-Bot/`. Обновите код и запустите setup:

```bash
cd ~/AI-Digest-Bot
git pull
CERTBOT_EMAIL=you@brieflybot.pro bash landing/scripts/server-setup.sh
```

Скрипт:
1. Копирует `briefly-landing.html` → `landing/www/index.html`
2. Копирует PDF из `docs/`
3. Кладёт `brieflybot.pro.conf` в `~/cv_portfolio/nginx/conf.d/`
4. Выпускает SSL через certbot (webroot)
5. Переключает на HTTPS-конфиг
6. Делает `docker compose exec nginx nginx -s reload`

### Шаг 4 — Проверка

```bash
curl -I http://brieflybot.pro/
curl -I https://brieflybot.pro/privacy-policy
certbot renew --dry-run
```

### Обновление только лендинга

```bash
cd ~/AI-Digest-Bot && git pull
bash landing/scripts/server-setup.sh
# без CERTBOT_EMAIL — сертификат уже есть, только обновит файлы
```

---

## Gmail OAuth

`.env` бота:

```env
GMAIL_REDIRECT_URI=https://brieflybot.pro/oauth/gmail/callback
```

Nginx проксирует `/oauth/` → `host.docker.internal:8080` (бот в docker на хосте).

Если OAuth не работает, на сервере:

```bash
OAUTH_UPSTREAM=172.17.0.1:8080 bash landing/scripts/server-setup.sh
```

---

## Ссылка на бота в лендинге

В `briefly-landing.html`:

```javascript
const BOT_URL = 'https://t.me/YourBotUsername';
```

---

## Деплой с Windows

`bash` на Windows нет — **всё делается на сервере** через `git pull` + `server-setup.sh`.

Альтернатива: залить файлы через WinSCP в `~/AI-Digest-Bot/landing/www/` и conf в `~/cv_portfolio/nginx/conf.d/`.
