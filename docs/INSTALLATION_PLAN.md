# План и текущий статус установки

Первый экспериментальный bootstrap находится в `scripts/install.sh`. Он рассчитан на ARM64 Termux и уже умеет устанавливать локальный runtime, создавать отдельный private repo пользователя, загружать operational template, запускать listener и поднимать Cloudflare Quick Tunnel. Скрипт ещё не прошёл полный end-to-end тест на чистом Android; до релиза его статус остаётся экспериментальным.

## Что нужно пользователю

- Android с поддерживаемой архитектурой (первый профиль — ARM64).
- Termux из выбранного поддерживаемого источника.
- GitHub account.
- AI assistant и подтверждённый write-capable канал для mailbox (GitHub connector ChatGPT может быть read-only).
- Сеть для GitHub и Cloudflare Quick Tunnel.

### Android приложения и плагины

1. **Termux** — обязателен.
2. **Termux:API** — необязателен для базового Bridge. Нужен, если позднее включены Android-функции. Для работы требуются Android-приложение Termux:API и CLI package `termux-api` внутри Termux.
3. **Termux:Boot** — необязателен. Нужен только если пользователь хочет попытаться запускать Bridge после перезагрузки Android. Не устанавливать и не включать без отдельного согласия.

Termux и все plugin APK должны быть из одного источника сборки/подписи. Не смешивать F-Droid и GitHub builds. Bootstrap не может незаметно установить Android APK-плагины.

## Что делает текущий install.sh

1. Проверяет native Termux и ARM64.
2. Устанавливает через `pkg` Python, Python cryptography, Git, GitHub CLI, curl, jq и cloudflared.
3. Клонирует публичный исходный проект в локальную папку приложения и создаёт отдельное Python venv с доступом к Termux-native cryptography package.
4. Проводит пользователя через GitHub CLI browser authorization, если вход ещё не выполнен.
5. Создаёт отдельный private repository в аккаунте пользователя и проверяет owner/visibility.
6. Загружает только чистый operational template.
7. Создаёт локальную конфигурацию с точными repository/ref/audience и persistent state path.
8. Запускает локальный listener на loopback.
9. Поднимает Cloudflare Quick Tunnel, проверяет внешний health endpoint и публикует URL в Actions variable `BRIDGE_TUNNEL_URL`.
10. Не включает Termux:Boot и не создаёт ненужные SSH private keys.

## Секреты и конфигурация

- Публичный репозиторий никогда не получает пользовательские секреты.
- Private operational repository содержит только workflow и mailbox.
- GitHub CLI credential хранится самим GitHub CLI.
- OIDC JWT краткоживущий, запрашивается workflow на каждый запуск и не сохраняется как постоянный секрет.
- Cloudflare Quick Tunnel не требует пользовательского SSH private key.
- Локальный конфиг и replay state хранятся вне Git с ограниченными правами.
- Не выводить credential или private key в логи и диагностику.

## Idempotency / resume

- Повторный запуск должен сохранять локальную конфигурацию и не создавать новый private repo.
- Установочный state фиксирует repository, чтобы продолжить создание после прерывания.
- При обновлении исходников используется fast-forward; локальные изменения не должны молча затираться.
- Не перезаписывать чужой repository или неизвестные Termux файлы.
- Полная проверка восстановления на чистом устройстве ещё не завершена.

## Авторизация

Предпочтительно использовать GitHub CLI browser/device auth. Не создавать PAT вручную и не передавать credential в чат. Разделять GitHub CLI user auth и Actions OIDC. Не обещать бессрочную авторизацию.

## Tunnel

Первый provider — Cloudflare Quick Tunnel:
- без Cloudflare account и собственного домена;
- временный случайный `trycloudflare.com` hostname;
- URL меняется после перезапуска;
- нет SLA, до 200 concurrent requests, без SSE;
- URL публичный, поэтому безопасность webhook обеспечивается OIDC verification, а не секретностью адреса.

Для стабильного hostname/production понадобится отдельная настройка named Cloudflare Tunnel. Она не включена в текущий бесплатный bootstrap.

## Что ещё проверить перед релизом

- Установка с нуля на чистом Termux ARM64.
- Наличие `python-cryptography` и `cloudflared` в конкретном Termux package source.
- Реальный GitHub device/browser login и создание private repo.
- Полный цикл команды от изменения mailbox до terminal result.
- Повтор команды после потери HTTP ответа и recovery после аварийного завершения.
- Поведение при остановке Android фоновых процессов и смене Quick Tunnel URL.
- Безопасное управление start/stop/status и opt-in для Termux:Boot.
