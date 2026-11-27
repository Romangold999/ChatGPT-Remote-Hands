# План и текущий статус установки

Первый экспериментальный bootstrap находится в scripts/install.sh. Он рассчитан на native Termux ARM64. До релиза нужны clean install на отдельном устройстве/профиле и end-to-end проверка полного цикла команды.

## Целевая архитектура

Реализация повторяет рабочий Termux Push Bridge и работает по push-событиям:

1. GPT записывает push-bridge/command.json со статусом ready в приватный operational repository.
2. Push запускает GitHub Actions.
3. Actions checkout-ит точный commit, получает OIDC JWT и отправляет через tunnl.gg только событие с repository/ref/after/timestamp.
4. Termux проверяет OIDC и событие, затем fetch-ит command.json по точному SHA.
5. Termux выполняет bash -lc с timeout.
6. Termux записывает result.json и подтверждает команду через GitHub Contents API.
7. GPT читает result.json и при необходимости отправляет следующую команду новым push.

Termux не опрашивает GitHub и не делает запросы за заданиями по таймеру. Keepalive туннеля обращается только к собственному /health endpoint и не проверяет mailbox.

## Что делает install.sh

1. Проверяет native Termux, ARM64 и интерактивную сессию.
2. Устанавливает Python, cryptography, Git, GitHub CLI, curl, jq и OpenSSH.
3. Клонирует публичный проект в отдельный каталог и создаёт Python venv.
4. Проводит GitHub CLI browser/device authorization.
5. Создаёт отдельный private operational repository пользователя.
6. Загружает clean template с workflow, command.json, result.json и tunnel-url.txt.
7. Настраивает OIDC audience termux-push-bridge, repository/ref, локальный state и listener port 18767.
8. Генерирует отдельный Ed25519 SSH key для tunnl.gg.
9. Помогает зарегистрировать ключ для stable URL.
10. Запускает локальный listener и отдельный tunnel supervisor.
11. Проверяет локальный и внешний /health.
12. Записывает актуальный tunnel URL в push-bridge/tunnel-url.txt через GitHub CLI.

Повторный запуск должен безопасно продолжать установку, не создавать лишние репозитории и не затрагивать другие Bridge установки.

## GitHub authorization

GitHub CLI credential остаётся под управлением gh. Bridge получает его в память через gh auth token, чтобы fetch-ить command.json и публиковать result.json/command acknowledgement. Credential не копируется в config.json, не передаётся в webhook и не выводится в лог.

GitHub CLI authorization должна иметь Contents read/write в личном operational repo. GitHub Actions workflow использует только:
- contents: read — checkout приватного operational repository;
- id-token: write — получение короткоживущего OIDC JWT с audience termux-push-bridge.

Не путать локальную GitHub CLI authorization с OIDC токеном Actions.

## OIDC и event validation

Listener проверяет RS256/JWKS, issuer, audience, точные repository/ref, event_name=push, exp/iat/nbf и jti. В теле события проверяются repository/ref, 40-символьный commit SHA и timestamp. Команда загружается по точному SHA события, а не по изменяемому HEAD ветки.

## Shell execution

Команда выполняется через bash -lc в HOME Termux. Поддерживаются stdout, stderr, exit code и timeout от 1 до 3600 секунд. Максимальная длина команды — 20 000 символов. Это полноценное исполнение в рамках Android app sandbox, не root и не отдельная sandbox-среда.

Доступ на запись в push-bridge/command.json фактически даёт право выполнять команды от имени пользователя Termux. Operational repo обязан быть private.

## Tunnel

Используется tunnl.gg reverse SSH tunnel с отдельным Ed25519 ключом на каждую установку. URL хранится в push-bridge/tunnel-url.txt. Supervisor переподключается после обрыва; health ping раз в 55 минут нужен только для поддержания туннеля. Публичный tunnel URL не является паролем.

## Проверки перед релизом

- clean install на чистом Termux ARM64;
- GitHub browser authorization и private repo creation;
- создание mailbox и workflow;
- отдельная регистрация tunnl.gg SSH key;
- OIDC event проходит на реальный listener;
- команда загружается по SHA события;
- shell выполняет команду, timeout и non-zero exit отражаются правильно;
- Termux публикует result.json и ack;
- GPT может прочитать результат и отправить следующую команду;
- replay, wrong repo/ref, stale event и concurrent command отклоняются;
- reconnect туннеля не создаёт дублирующих исполнений;
- пользовательский рабочий Bridge и его ключи/порт остаются нетронутыми.

До завершения этих проверок проект остаётся experimental.
