# Архитектура ChatGPT Remote Hands

## Поток данных — push, без polling

1. ChatGPT или write-capable канал записывает push-bridge/command.json со статусом ready в приватный operational repository.
2. Push по push-bridge/command.json запускает GitHub Actions.
3. Workflow checkout-ит точный commit SHA, получает короткоживущий OIDC JWT с audience termux-push-bridge и отправляет через tunnl.gg только event metadata: repository, ref, after SHA и timestamp.
4. Termux listener проверяет RS256/JWKS, issuer, audience, repository, ref, event_name=push, временные claims и jti.
5. Termux по точному SHA получает command.json через GitHub Contents API с локальной авторизацией GitHub CLI.
6. Persistent replay/sequence state защищает от повторного исполнения и конкурентных команд.
7. Worker выполняет bash -lc в HOME Termux с timeout.
8. Termux записывает result.json и подтверждает статус command.json через GitHub Contents API.
9. ChatGPT читает result.json, сверяет ID/sequence/status и решает, нужна ли следующая команда.

**Termux не опрашивает GitHub за командами.** Новая команда приходит только по push event. HTTP 202 означает принятие события, а не завершение shell execution. Туннельный health ping не является polling mailbox.

## Компоненты

- Python listener: loopback-only HTTP server на 127.0.0.1:18767.
- OIDC verifier: PyJWT/JWKS, RS256, issuer, audience, repository/ref/event claims, timestamps, jti.
- Mailbox client: GitHub Contents API; локальный token из gh auth token используется только в памяти.
- Protocol parser: строгая схема shell envelope, ID/sequence/status/timeout/command length.
- ReplayState: атомарный persistent state, replay protection, idempotent result cache.
- Executor: subprocess.run(["bash","-lc", command]) с timeout, stdout, stderr и exit code.
- Lifecycle CLI: start/stop/status/logs для listener.
- Tunnel manager: отдельный SSH reverse tunnel supervisor, stable URL, pinned host key, reconnect и health keepalive.
- Operational template: push-triggered workflow, command/result mailbox, tunnel-url.txt.
- Installer: native Termux ARM64 bootstrap, private repo, GitHub CLI authorization, dedicated SSH key, tunnel registration.

## Формат mailbox

command.json содержит version, id, sequence, status=ready, operation=shell, approval, timeout_seconds и command (до 20 000 символов).

result.json содержит matching id/sequence, terminal status, timestamps, exit_code, stdout, stderr и error.

Tunnel URL хранится в push-bridge/tunnel-url.txt. Workflow запускается только при изменении push-bridge/command.json, поэтому обновление tunnel URL не создаёт цикл запуска.

## Права и границы

Shell выполняется с правами Termux app user. Это полноценное исполнение команд внутри Android sandbox, но не root и не удалённый рабочий стол. Write access к push-bridge/command.json фактически даёт command authority над Termux user account. Operational repo обязан быть private.

Actions permissions:
- contents: read — checkout private repository;
- id-token: write — OIDC token.

Termux использует локальную GitHub CLI authorization с Contents read/write для чтения команды и публикации результата. Токен не передаётся в webhook и не записывается в Bridge config.

## Хранилище

Публичный репозиторий: только generic source, templates, docs, tests.
Локальный Android: config, replay state, logs, PID, dedicated SSH private key, GitHub CLI credential (управляется gh).
Private operational repo: workflow, command/result mailbox, tunnel URL.
GitHub Actions: короткоживущий OIDC JWT только во время run.

## Статус и дальнейшие проверки

Unit tests и CI проверяют protocol, shell executor, state, OIDC claims и webhook acceptance. Это не заменяет clean install и end-to-end проверку на отдельном Termux устройстве с реальным tunnl.gg, GitHub API и write/read integration channel.

До релиза нужны:
- clean Termux ARM64 install;
- реальный GitHub auth и private repo bootstrap;
- реальная команда от push event до result mailbox;
- проверка отказов OIDC, replay, timeout, non-zero exit, concurrent command;
- reconnect tunnel и восстановление после перезапуска Android;
- безопасный resume installer и background lifecycle.
