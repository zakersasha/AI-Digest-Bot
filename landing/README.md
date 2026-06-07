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

### Шаг 2 — docker-compose cv_portfolio

В `~/cv_portfolio/docker-compose.yml` в сервис **nginx** добавьте только:

```yaml
extra_hosts:
  - "host.docker.internal:host-gateway"
```

и один volume:

```yaml
- /root/AI-Digest-Bot/landing/www:/var/www/brieflybot.pro:ro
```

Certbot-пути `./certbot/conf` и `./certbot/www` **уже есть** — их не трогаем.

Полный пример — `landing/cv_portfolio.volumes.example.txt`.

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

### HTTPS редиректит на CV-сайт?

**Симптом:** `http://brieflybot.pro` — лендинг Briefly, `https://brieflybot.pro` — CV-портфолио.

**Причина:** на порту 443 нет `server_name brieflybot.pro` (только HTTP-конфиг). Nginx отдаёт CV как `default_server`.

**Исправление на сервере:**

```bash
cd ~/AI-Digest-Bot
CERTBOT_EMAIL=ваш@email.com bash landing/scripts/fix-https.sh
```

Или вручную:

```bash
# 1. Есть ли сертификат?
ls ~/cv_portfolio/certbot/conf/live/brieflybot.pro/

# 2. Если нет — выпустить (webroot уже в docker)
certbot certonly --webroot \
  -w ~/cv_portfolio/certbot/www \
  --config-dir ~/cv_portfolio/certbot/conf \
  --work-dir ~/cv_portfolio/certbot/work \
  --logs-dir ~/cv_portfolio/certbot/logs \
  -d brieflybot.pro -d www.brieflybot.pro \
  --email ваш@email.com --agree-tos --no-eff-email

# 3. HTTPS-конфиг вместо HTTP-only
cp ~/AI-Digest-Bot/landing/nginx/brieflybot.pro.conf \
   ~/cv_portfolio/nginx/conf.d/brieflybot.pro.conf

# 4. Проверка и reload
cd ~/cv_portfolio
docker compose exec nginx nginx -t
docker compose exec nginx nginx -s reload
```

Убедитесь, что в CV-конфиге (`nginx/conf.d/*.conf`) на `443` указан **конкретный** `server_name` вашего CV-домена, а не `default_server` без ограничений.

**Ошибка** `options-ssl-nginx.conf failed` — в Docker certbot часто не кладёт этот файл. Конфиг Briefly использует встроенные SSL-настройки, certbot-файлы не нужны.

### Шаг 4 — Проверка

```bash
curl -I http://brieflybot.pro/
curl -I https://brieflybot.pro/privacy-policy
certbot renew --dry-run
```

### Обновление лендинга или legal-страниц

Nginx отдаёт файлы из **`landing/www/`**:

```
landing/www/
  index.html
  privacy-policy.html
  terms-of-service.html
  assets/shared.css
```

Исходники legal: `landing/privacy-policy.html`, `landing/terms-of-service.html` (контент из `docs/`).

```bash
cd ~/AI-Digest-Bot
git pull
bash landing/scripts/sync-site.sh
cp landing/nginx/brieflybot.pro.conf ~/cv_portfolio/nginx/conf.d/brieflybot.pro.conf
cd ~/cv_portfolio && docker compose exec nginx nginx -t && docker compose exec nginx nginx -s reload
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
