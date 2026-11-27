# Протокол команд mailbox

Протокол v1 определяет JSON envelope, который GitHub Actions передаёт локальному listener. Валидатор, OIDC-проверка, replay state и исполнитель являются отдельными слоями.

## Файлы приватного operational repository

- `mailbox/command.json` — входящая команда.
- `mailbox/result.json` — результат последней команды.
- Actions variable `BRIDGE_TUNNEL_URL` — текущий HTTPS tunnel endpoint конкретного пользователя.

## Envelope версии 1

Обязательные поля:

| Поле | Тип | Правило |
|---|---|---|
| `version` | integer | строго `1` |
| `id` | string | canonical UUID |
| `sequence` | integer | положительное число; следующий ожидаемый номер |
| `operation` | string | только операция из allowlist |

Дополнительные поля:

| Поле | Тип | Правило |
|---|---|---|
| `status` | string | для новой команды только `pending` |
| `arguments` | object | в текущей версии операции не принимают аргументы |
| `approval` | boolean | по умолчанию `false`; само по себе не подтверждает опасное действие |
| `timeout_seconds` | integer | от 1 до 60; по умолчанию 10 |

Лимит входного JSON envelope — 16 KiB. Неизвестные поля отклоняются.

### Начальный allowlist

- `bridge.status`
- `bridge.health`
- `system.info`

Эти три операции реализованы без вызова shell или subprocess. Произвольное поле `command`, shell-строка и операция `shell.exec` не поддерживаются. Новая операция добавляется только вместе с реализацией, схемой аргументов, тестами, документацией и security review.

## OIDC и mailbox gates

Перед исполнением listener:

1. Проверяет JWT подпись по GitHub JWKS и алгоритм RS256.
2. Проверяет issuer `https://token.actions.githubusercontent.com`, audience `termux-bridge`, временные claims.
3. Сверяет точные `repository` и `ref` с локальной конфигурацией пользователя.
4. Проверяет обязательный `jti` и сохраняет его в persistent replay state.
5. Проверяет, что sequence — следующий ожидаемый номер.
6. Парсит envelope и допускает только allowlist.

Локальный HTTP listener привязан к `127.0.0.1:18766`; внешний доступ должен идти через HTTPS tunnel. Listener не принимает произвольные команды.

## Результат

Workflow сохраняет в `mailbox/result.json` JSON-объект с полями:

- `version`
- `id`
- `sequence`
- `status` (`completed` или `failed`)
- `started_at`
- `finished_at`
- `duration_seconds`
- `exit_code`
- `data`
- `error`

Перед публикацией workflow проверяет, что ответ содержит структурированный result. Клиент должен дополнительно сверить ID и sequence с исходной командой.

## Ограничения текущей реализации

- Одна команда за раз; workflow concurrency сериализует dispatch.
- Persistent state защищает от повторного jti и неправильного sequence.
- Восстановление, если listener уже исполнил команду, но workflow не успел сохранить result, ещё требует отдельного idempotency механизма.
- Timeout envelope не даёт права на произвольный долгий процесс; текущие операции — короткие встроенные функции.
- Для больших файлов требуется отдельный chunked transfer с SHA-256, порядком частей, лимитом размера и TTL.

HTTP 200 означает, что listener вернул результат. Успешный workflow сам по себе не заменяет проверку содержимого `mailbox/result.json`.
