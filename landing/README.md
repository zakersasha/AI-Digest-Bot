# brieflybot.pro

Статика лежит в **`landing/www/`** — она же монтируется в nginx.

```
landing/www/
  index.html
  privacy-policy.html
  terms-of-service.html
```

Docker volume в `cv_portfolio/docker-compose.yml`:

```yaml
- /root/AI-Digest-Bot/landing/www:/var/www/brieflybot.pro:ro
```

Nginx conf: `landing/nginx/brieflybot.pro.conf` → `~/cv_portfolio/nginx/conf.d/`

**Деплой:** `git pull` на сервере. Всё.

**URL для Google:**
- https://brieflybot.pro/privacy-policy
- https://brieflybot.pro/terms-of-service
