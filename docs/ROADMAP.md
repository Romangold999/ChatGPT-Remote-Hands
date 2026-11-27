# Roadmap

## Этап 1 — push-event runtime

- [x] Loopback listener на 127.0.0.1.
- [x] GitHub OIDC RS256/JWKS verification.
- [x] Проверка issuer, audience, repository, ref, event_name, временных claims и jti.
- [x] Получение команды из private mailbox по точному commit SHA.
- [x] Полноценный Bash executor через bash -lc.
- [x] stdout, stderr, exit code и timeout.
- [x] Persistent replay/sequence state.
- [x] Сериализация команд и idempotent result cache.
- [x] Публикация result.json и acknowledgement самим Termux.
- [x] Unit/integration tests и CI.

Критерий выхода: локальный runtime принимает только проверенные push events, исполняет одну команду и публикует terminal result.

## Этап 2 — operational repository

- [x] Private repo template с command/result mailbox.
- [x] Push-only workflow, который отправляет только event metadata.
- [x] Workflow permissions contents:read и id-token:write.
- [x] push-bridge/tunnel-url.txt.
- [x] Отдельный private repo пользователя в installer draft.
- [ ] Проверить GitHub CLI Contents read/write на clean install.
- [ ] Протестировать две независимые пользовательские установки.

## Этап 3 — tunnl.gg

- [x] Stable SSH reverse tunnel.
- [x] Dedicated Ed25519 key per installation.
- [x] Pinned host key.
- [x] Reconnect supervisor.
- [x] External health check and 55-minute tunnel keepalive.
- [x] Publish stable URL to push-bridge/tunnel-url.txt.
- [ ] Проверить reconnect и stable URL на реальном Android.
- [ ] Проверить работу при смене сети и Android battery restrictions.

## Этап 4 — installer и background lifecycle

- [x] Первый bootstrap draft для native Termux ARM64.
- [x] GitHub CLI browser authorization.
- [x] Private operational repo creation и template copy для новой установки.
- [x] Separate SSH identity и registration flow.
- [ ] Clean install и resume test на чистом Termux.
- [ ] Safe upgrade existing installation without overwriting user files.
- [ ] Background supervisor/restart behavior for listener and tunnel.
- [ ] Opt-in wake lock / Termux:Boot, with correct install and permission checks.
- [ ] Doctor/repair commands and health diagnostics.

## Этап 5 — release hardening

- [ ] Real end-to-end test: ChatGPT write → push → Termux execute → result → ChatGPT read.
- [ ] Recovery after device/network/process interruption.
- [ ] Chunked transfer for large files.
- [ ] Security audit and dependency review.
- [ ] Release notes and verified beginner installation guide.

## Не обещается

- Гарантированный uptime 24/7 на Android.
- Неограниченный бесплатный tunnel.
- Root-доступ или обход Android sandbox.
- Постоянная авторизация без возможности отзыва.
- Возможность записи через read-only ChatGPT connector.
