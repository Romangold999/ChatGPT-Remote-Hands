# Диагностика и устранение неисправностей

## Общий порядок

1. Не переустанавливать сразу.
2. Зафиксировать точную ошибку и этап.
3. Проверить status, процессы, PID, health и лог.
4. Проверить tunnel connectivity/URL.
5. Проверить Actions run/job/step logs.
6. Проверить command/result ID, sequence, status.
7. Проверить OIDC claims validation без вывода JWT.
8. Сформулировать первопричину.
9. Сделать backup и внести минимальное исправление с согласием.
10. Повторить end-to-end тест.

## Матрица ошибок

| Симптом | Возможные причины | Что проверять |
|---|---|---|
| gh: command not found | CLI не установлен/PATH | command -v gh, Termux package source |
| gh auth status failed | login revoked/expired/policy | gh auth status, повторный browser login |
| repo create denied | scopes/permissions/policy | gh auth status, gh api user, repo create error |
| Actions не запускается | branch/path filter, workflow disabled | workflow file, Actions settings, run list |
| Actions permission denied | permissions block / workflow scope | workflow permissions, repository settings |
| OIDC token unavailable | id-token: write missing | job permissions |
| OIDC audience mismatch | workflow audience != listener config | audience configuration on both sides |
| JWT signature invalid | JWKS/key rotation/clock | JWKS fetch, kid, signature, system time |
| repository/ref rejected | claims mismatch | repository, ref, issuer, workflow branch |
| HTTP 202, результата нет | событие принято, но выполнение не завершено | result mailbox, local log, daemon |
| tunnel unreachable | process stopped, URL rotated, network | tunnel process, URL file, SSH log |
| bridge stopped | process killed, crash, Android background limit | PID, log, health, battery restrictions |
| duplicate/replay | повторный jti/id/sequence | journal, mailbox state |
| result stale | неправильная branch/path/cache | exact repo/ref/commit and result id |
| storage permission denied | Termux shared storage permission | termux-setup-storage, Android app permission |

## Безопасный сбор диагностики

Разрешено собирать версии, пути бинарников, статусы процессов, exit codes, имена конфигурационных ключей, file modes, health status и отредактированные логи.

Запрещено собирать/показывать содержимое PAT, OAuth credentials, OIDC JWT, private SSH key, HMAC secret, cookies и полные секретные конфиги.

## Терминальные статусы

Не предполагать перечень terminal statuses по памяти. Проверить схему/код текущей версии. Для mailbox не отправлять новую команду, пока текущая не терминальна.
