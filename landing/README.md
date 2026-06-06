# Briefly landing — brieflybot.pro

Статический лендинг + публичные Privacy Policy и Terms of Service для Google OAuth и маркетинга.

## URL для Google Cloud Console

| Документ | URL |
|----------|-----|
| Privacy Policy | `https://brieflybot.pro/privacy-policy` |
| Terms of Service | `https://brieflybot.pro/terms-of-service` |
| Homepage | `https://brieflybot.pro/` |
| Gmail OAuth redirect | `https://brieflybot.pro/oauth/gmail/callback` |

Короткие алиасы: `/privacy` → `/privacy-policy`, `/terms` → `/terms-of-service`.

## Структура

```
landing/
  index.html              ← копия briefly-landing.html (деплой)
  docs/
    briefly-privacy-policy.pdf
    briefly-terms-of-service.pdf
  nginx/
    brieflybot.pro.http.conf   ← до получения SSL
    brieflybot.pro.conf          ← production HTTPS
  scripts/
    deploy.sh
    setup-ssl.sh
```

## Деплой на сервер с уже работающим nginx

Ваш основной `nginx.conf` **не трогаем** — только добавляем файл в `conf.d/`:

```bash
include /etc/nginx/conf.d/*.conf;
```

### 1. DNS

A-запись `brieflybot.pro` → IP сервера.  
Опционально `www.brieflybot.pro` → тот же IP (редирект на apex).

### 2. Загрузить файлы

С локальной машины (из корня репозитория):

```bash
bash landing/scripts/deploy.sh root@YOUR_SERVER_IP
```

На сервере вручную:

```bash
mkdir -p /var/www/brieflybot.pro/docs /var/www/certbot
# скопировать index.html и PDF из landing/
chown -R nginx:nginx /var/www/brieflybot.pro /var/www/certbot
```

### 3. Nginx (первый раз — без SSL)

```bash
cp landing/nginx/brieflybot.pro.http.conf /etc/nginx/conf.d/brieflybot.pro.conf
nginx -t && systemctl reload nginx
```

Проверка: `http://brieflybot.pro/` и PDF по HTTP.

### 4. Let's Encrypt + автообновление

```bash
CERTBOT_EMAIL=you@brieflybot.pro sudo -E bash landing/scripts/setup-ssl.sh
```

Скрипт:
1. Ставит HTTP-конфиг с `/.well-known/acme-challenge/`
2. Выпускает сертификат через `certbot certonly --webroot`
3. Подключает HTTPS-конфиг
4. Включает `certbot.timer` и hook `reload nginx` после renew

Проверка продления:

```bash
certbot renew --dry-run
```

### 5. Обновление только статики

```bash
bash landing/scripts/deploy.sh root@YOUR_SERVER_IP
# SSL-конфиг менять не нужно
```

## Gmail OAuth

В `.env` бота:

```env
GMAIL_REDIRECT_URI=https://brieflybot.pro/oauth/gmail/callback
```

В Google Cloud Console → OAuth client → Authorized redirect URIs — тот же URL.

Nginx проксирует `/oauth/` на `127.0.0.1:8080` (docker-compose `bot` service).

## Лендинг: ссылка на бота

В `briefly-landing.html` / `landing/index.html` замените:

```javascript
const BOT_URL = 'https://t.me/YourBotUsername';
```

## Конфликт с другими сайтами

Конфиг `brieflybot.pro.conf` слушает только `server_name brieflybot.pro www.brieflybot.pro` — существующие vhost'ы на том же nginx не затрагиваются.

Порт 443/80 общие: убедитесь, что другой default_server не перехватывает этот домен (обычно `server_name` решает это автоматически).
