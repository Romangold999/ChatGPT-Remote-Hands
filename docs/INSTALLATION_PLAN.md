# План и текущий статус установки

Первый экспериментальный bootstrap находится в `scripts/install.sh`. Он рассчитан на ARM64 Termux и уже умеет устанавливать локальный runtime, создавать отдельный private repo пользователя, загружать operational template, запускать listener и поднимать tunnl.gg SSH reverse tunnel. Скрипт ещё не прошёл полный end-to-end тест на чистом Android; до релиза его статус остаётся экспериментальным.

## Что нужно пользователю

- Android с поддерживаемой архитектурой (первый профиль — ARM64).
- Termux из выбранного поддерживаемого источника.
- GitHub account.
- AI assistant и подтверждённый write-capable канал для mailbox (GitHub connector ChatGPT может быть read-only).
- Сеть для GitHub и tunnl.gg SSH reverse tunnel.

### Android приложения и плагины

1. **Termux** — обязателен.
2. **Termux:API** — необязателен для базового Bridge. Нужен, если позднее включены Android-функции. Для работы требуются Android-приложение Termux:API и CLI package `termux-api` внутри Termux.
3. **Termux:Boot** — необязателен. Нужен только если пользователь хочет попытаться запускать Bridge после перезагрузки Android. Не устанавливать и не включать без отдельного согласия.

Termux и все plugin APK должны быть из одного источника сборки/подписи. Не смешивать F-Droid и GitHub builds. Bootstrap не может незаметно установить Android APK-плагины.

## Что делает текущий install.sh

1. Проверяет native Termux и ARM64.
2. Устанавливает через `pkg` Python, Python cryptography, Git, GitHub CLI, curl, jq и OpenSSH.
3. Клонирует публичный исходный проект в локальную папку приложения и создаёт отдельное Python venv с доступом к Termux-native cryptography package.
4. Проводит пользователя через GitHub CLI browser authorization, если вход ещё не выполнен.
5. Создаёт отдельный private repository в аккаунте пользователя и проверяет owner/visibility.
6. Загружает только чистый operational template.
7. Создаёт локальную конфигурацию с точными repository/ref/audience и persistent state path.
8. Запускает локальный listener на loopback.
9. Поднимает стабильный tunnl.gg reverse tunnel через OpenSSH, проверяет внешний `/health` и публикует URL в Actions variable `BRIDGE_TUNNEL_URL`.
10. Создаёт отдельный локальный Ed25519-ключ, проводит однократную регистрацию stable URL и не включает Termux:Boot.

## Секреты и конфигурация

- Публичный репозиторий никогда не получает пользовательские секреты.
- Private operational repository содержит только workflow и mailbox.
- GitHub CLI credential хранится самим GitHub CLI.
- OIDC JWT краткоживущий, запрашивается workflow на каждый запуск и не сохраняется как постоянный секрет.
- Для stable URL tunnl.gg нужен отдельный зарегистрированный Ed25519-ключ; private key остаётся на Android.
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

Первый provider — tunnl.gg поверх OpenSSH. Используется `stable@proxy.tunnl.gg` с отдельным зарегистрированным Ed25519-ключом. URL сохраняется при переподключениях. Бесплатный режим ограничен 3 туннелями на IP, 5 GB/сутки, 2 часами без HTTP-активности и 24 часами на сессию. Supervisor переподключает SSH и делает `/health` ping каждые 55 минут. Подробности — в `docs/TUNNEL.md`.

Для стабильного hostname/production понадобится отдельная настройка named tunnl.gg Tunnel. Она не включена в текущий бесплатный bootstrap.

## Что ещё проверить перед релизом

- Установка с нуля на чистом Termux ARM64.
- Наличие `python-cryptography` и `OpenSSH` в конкретном Termux package source.
- Реальный GitHub device/browser login и создание private repo.
- Полный цикл команды от изменения mailbox до terminal result.
- Повтор команды после потери HTTP ответа и recovery после аварийного завершения.
- Поведение при остановке Android фоновых процессов и смене Quick Tunnel URL.
- Безопасное управление start/stop/status и opt-in для Termux:Boot.
