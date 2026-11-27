# Архитектура Android Remote Bridge

## Поток данных

1. AI assistant или другой write-capable канал записывает команду в mailbox приватного репозитория пользователя.
2. Push файла `mailbox/command.json` запускает GitHub Actions.
3. Workflow получает краткоживущий OIDC ID token с audience `termux-bridge`.
4. Workflow отправляет JSON-команду через HTTPS tunnel на локальный listener Android.
5. Listener проверяет подпись JWT по GitHub JWKS, issuer, audience, точные claims repository/ref и временные claims.
6. Listener проверяет envelope, persistent sequence и jti replay protection.
7. Выполняется только операция из локального allowlist; произвольный shell не поддерживается.
8. Listener возвращает структурированный результат workflow.
9. Workflow записывает результат в `mailbox/result.json` приватного репозитория.
10. AI assistant отдельно читает результат и проверяет ID, sequence и status.

## Реализовано в текущем коде

- Listener на стандартной библиотеке Python, привязанный только к `127.0.0.1:18766`.
- Endpoint `GET /health` и `POST /webhook`.
- OIDC JWT verification через GitHub JWKS и PyJWT: RS256, issuer, audience, exp/iat, repository, ref и jti.
- Persistent replay/sequence state с атомарной заменой файла, правами 0600 и кэшированием последнего результата для безопасного повтора той же команды.
- Envelope parser с лимитом 16 KiB и строгим allowlist.
- Executor без shell/subprocess для `bridge.status`, `bridge.health`, `system.info`.
- Шаблон operational repo: workflow вызывает tunnel, затем сохраняет JSON result в приватный mailbox.
- CI устанавливает пакет и зависимости и запускает unit tests.

Это начальный рабочий слой, а не готовый пользовательский установщик. В частности, ещё нет end-to-end проверки с реальным tunnel provider, полной автоматической настройки GitHub repo и устойчивого восстановления незавершённого dispatch после аварийного завершения процесса.

## Границы и места хранения

### Публичный репозиторий (этот проект)
Только универсальный код, чистые шаблоны, документация и тесты. Запрещено добавлять пользовательские или разработческие токены, OAuth/PAT, OIDC JWT, пароли, SSH private keys, HMAC secrets, приватные конфиги, персональные tunnel URL, логи и результаты команд.

### Приватный operational repository пользователя
Отдельный репозиторий для каждого пользователя. В нём находятся mailbox и workflow. Персональный tunnel URL хранится как Actions variable `BRIDGE_TUNNEL_URL`, а не в публичном шаблоне. Не помещать туда private keys, PAT/OAuth credentials, HMAC secrets или долговременные bearer tokens.

### Локальное Android-хранилище
Локальная конфигурация и persistent replay state хранятся вне Git. Bootstrap должен создавать их на устройстве, ограничивать доступ к файлам и не печатать секреты. Private key никогда не покидает устройство.

### GitHub Actions
OIDC JWT запрашивается во время workflow с минимальными permissions. В шаблоне используются `contents: write` для публикации результата и `id-token: write` для краткоживущего OIDC токена. JWT не сохраняется как постоянный секрет.

## Termux и Android add-ons

- Termux — обязательная базовая среда.
- Termux:API — опционален. Для Android API функций нужны APK приложения Termux:API и CLI package `termux-api` внутри Termux.
- Termux:Boot — опционален и настраивается только после явного opt-in.
- Все Termux APK и plugin APK должны быть из одного совместимого источника подписи.

## Workflow security

- Concurrency lock сериализует dispatch.
- Third-party Actions закреплены по immutable commit SHA.
- OIDC audience, repository и ref проверяются локальным listener.
- Workflow принимает только HTTPS URL и ограничивает время HTTP-запроса.
- Результат публикуется в operational repo; успешный HTTP ответ и успешный workflow не следует путать с проверкой terminal result.

## Что ещё требуется реализовать и проверить

- Автоматическое восстановление после аварийного завершения до сохранения terminal result.
- Полная автоматизация создания private repo и настройки Actions variable.
- Tunnel provider manager, регистрация, reconnect и URL rotation.
- Bootstrap и resume на чистом Termux.
- Lifecycle CLI (status/start/stop/logs) и установка как фонового процесса.
- Более широкие integration/security tests, включая реальные OIDC claims и end-to-end тест в отдельной тестовой инфраструктуре.
- Chunked transfer для больших payload.
