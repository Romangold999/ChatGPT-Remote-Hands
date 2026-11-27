# Архитектура Android Remote Bridge

## Поток данных

1. AI assistant формирует команду в mailbox приватного репозитория пользователя через доступный write-capable канал.
2. Push запускает GitHub Actions.
3. Workflow получает краткоживущий OIDC ID token с заданной audience.
4. Workflow отправляет событие через HTTPS tunnel на локальный listener Android.
5. Listener проверяет подпись JWT по GitHub JWKS и claims: issuer, audience, repository, ref, timestamps; применяет replay protection.
6. Listener проверяет mailbox, sequence и разрешённость операции.
7. Выполняется разрешённая операция с timeout и лимитом вывода.
8. Результат записывается в result mailbox приватного репозитория.
9. AI assistant отдельно читает результат и проверяет его ID/status.

## Границы и места хранения

### Публичный репозиторий (этот проект)
Только универсальный код, чистые шаблоны, документация и тесты. Запрещено добавлять пользовательские или разработческие токены, OAuth/PAT, OIDC JWT, пароли, SSH private keys, HMAC secrets, приватные конфиги, персональные tunnel URL, логи и результаты команд.

### Приватный operational repository пользователя
Отдельный репозиторий для каждого пользователя. В нём находятся mailbox, workflow и индивидуальные несекретные параметры. Не помещать туда private keys, PAT/OAuth credentials, HMAC secrets или долговременные bearer tokens. По возможности использовать OIDC для workflow identity.

### Локальное Android-хранилище
Bootstrap генерирует уникальные ключи и секреты непосредственно на устройстве. GitHub CLI credential хранится механизмом GitHub CLI. Приватный SSH key и локальная конфигурация должны иметь права доступа только владельцу приложения (например, chmod 600 для файлов, где применимо) и исключаться из Git/backup/export. Не печатать значения секретов, даже в debug mode.

### GitHub Actions
OIDC JWT запрашивается в момент выполнения workflow с минимальными permissions, обычно `contents: read` и `id-token: write`. JWT краткоживущий, проверяется локальным listener и не сохраняется как постоянный секрет. Дополнительные права выдаются только для конкретной обоснованной операции.

## Termux и Android add-ons

- Termux — обязательная базовая среда.
- Termux:API — опциональный Android plugin для вызова функций Android из CLI. Если проект использует его API, нужны APK приложения Termux:API и CLI package `termux-api` внутри Termux; запросить только необходимые Android permissions.
- Termux:Boot — опциональный plugin для запуска скриптов после перезагрузки. Установка, первый запуск приложения и создание boot script происходят только после явного opt-in. Не включать автозапуск по умолчанию.
- Все Termux APK и plugin APK должны быть из одного совместимого источника подписи. Не смешивать F-Droid/GitHub builds.

## Workflow security

- Минимальные permissions; дополнительные права только при доказанной необходимости.
- Concurrency lock сериализует dispatch.
- Third-party Actions закреплены по immutable commit SHA.
- OIDC audience, repository и ref генерируются для конкретного пользователя.
- Проверяются подпись, issuer, audience, repository, ref, timestamps и replay.
- HTTP 200/202 означает принятие события endpoint-ом, а не успешное выполнение команды.

## Security boundaries

- Listener привязан только к loopback-интерфейсу; публичный доступ только через туннель.
- Private key никогда не покидает устройство; tunnel provider получает только public key.
- Секреты не должны попадать в stdout/stderr, логи, Git history или отчёты.
- Команды выполняются с минимальными полномочиями, ограниченным временем и контролируемым выводом.
- Chunked transfer проверяет целостность частей, порядок, общий размер и срок жизни передачи.

## Что ещё требуется реализовать и проверить

- Полностью автоматизированный bootstrap и resume на чистом Termux.
- Определение необходимости Termux:API и безопасная установка CLI-пакета.
- Опциональная установка и opt-in настройка Termux:Boot.
- Генерация repository/ref/audience для каждого пользователя.
- Поддерживаемый write path для mailbox; GitHub connector ChatGPT может быть read-only.
- Tunnel registration, reconnect и URL rotation.
- Chunked transfer для больших payload.
- Полный end-to-end тест на отдельной тестовой среде.
