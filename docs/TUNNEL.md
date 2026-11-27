# Tunnel provider: Cloudflare Quick Tunnel

## Выбор для первого рабочего варианта

Для первого end-to-end сценария выбран **Cloudflare Quick Tunnel** через `cloudflared`.

Почему:
- не требуется Cloudflare account или собственный домен;
- создаёт публичный HTTPS URL для локального HTTP listener;
- официальный Termux package recipe для `cloudflared` существует;
- не нужно открывать входящий порт на роутере или телефоне.

Официальные документы:
- [Cloudflare Quick Tunnels](https://developers.cloudflare.com/tunnel/get-started/quick-tunnels/)
- [Cloudflare downloads](https://developers.cloudflare.com/tunnel/downloads/)
- [Termux cloudflared package recipe](https://github.com/termux/termux-packages/tree/master/packages/cloudflared)

## Установка и запуск

На Termux-профиле, где пакет доступен:

```bash
pkg update
pkg install cloudflared
```

Локальный listener должен быть запущен на `127.0.0.1:18766`. Для временного ручного теста:

```bash
cloudflared tunnel --no-autoupdate --url http://127.0.0.1:18766
```

В текущем проекте модуль `android_remote_bridge.tunnel` автоматизирует запуск Quick Tunnel, проверку локального и внешнего `/health`, извлечение URL и обновление Actions variable `BRIDGE_TUNNEL_URL` в индивидуальном private repository через GitHub CLI.

Команда после установки Python-пакета:

```bash
android-remote-bridge-tunnel start --config ~/.config/android-remote-bridge/config.json
android-remote-bridge-tunnel status --config ~/.config/android-remote-bridge/config.json
android-remote-bridge-tunnel stop --config ~/.config/android-remote-bridge/config.json
```

## Ограничения Quick Tunnel

Quick Tunnels предназначены Cloudflare для тестирования и разработки, а не для production:
- нет SLA и гарантии uptime;
- hostname случайный и меняется при каждом новом запуске;
- URL перестаёт работать после остановки процесса;
- максимум 200 одновременных запросов на Quick Tunnel; сверх лимита возвращается HTTP 429;
- Server-Sent Events (SSE) не поддерживаются;
- любой, кто знает URL, может обратиться к локальному сервису.

Поэтому listener не должен полагаться на секретность URL. Выполнение команд защищается проверкой короткоживущего GitHub OIDC JWT с точными claims repository/ref. Неавторизованный запрос к `POST /webhook` отклоняется. Внешний `GET /health` не возвращает конфигурацию или секреты.

## Важные замечания

- Android может остановить `cloudflared` в фоне. 24/7 не гарантируется.
- После перезапуска URL может измениться; tunnel manager должен обновить Actions variable.
- Если `pkg install cloudflared` недоступен в конкретной сборке Termux, установщик не должен скачивать случайный бинарник. Нужно показать поддерживаемый вариант установки/сборки либо остановиться с понятной ошибкой.
- Для стабильного hostname и production-сценария понадобится отдельная настройка named Cloudflare Tunnel с аккаунтом и доменом. Это не включается автоматически в первый бесплатный режим.
