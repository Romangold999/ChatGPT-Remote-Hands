# Архитектура Android Remote Bridge

## Поток данных

1. AI assistant формирует команду в mailbox приватного репозитория пользователя через доступный write-capable канал.
2. Push в настроенную ветку и путь запускает GitHub Actions.
3. Workflow получает короткоживущий OIDC ID token с заданной audience.
4. Workflow отправляет событие через HTTPS endpoint туннеля на локальный listener Android.
5. Listener проверяет подпись JWT по доверенному GitHub JWKS и claims: issuer, audience, repository, ref, timestamps; применяет replay protection.
6. Listener проверяет mailbox, sequence и разрешённость операции.
7. Выполняется команда в ограниченном режиме с timeout и лимитом вывода.
8. Результат записывается в result mailbox приватного репозитория.
9. AI assistant отдельно читает результат и проверяет его ID/status.

## Компоненты

- Публичный репозиторий: исходники, шаблоны, документация и тесты.
- Приватный operational repository: отдельный для каждого пользователя.
- GitHub Actions workflow: получает OIDC token и доставляет событие.
- Mailbox: входящая команда и результат.
- Локальный listener: привязан только к loopback-интерфейсу.
- Tunnel supervisor: поддерживает соединение и отслеживает изменение URL.
- Local bridge service: проверяет команды, запускает разрешённые операции и публикует результаты.

## Workflow security

- Минимальные permissions: `contents: read` и `id-token: write`; дополнительные права только при доказанной необходимости.
- Concurrency lock сериализует dispatch.
- Third-party Actions должны быть закреплены по immutable commit SHA.
- OIDC audience, repository и ref генерируются для конкретного пользователя.
- Проверяются подпись, issuer, audience, repository, ref, timestamps и replay.
- HTTP 200/202 означает принятие события endpoint-ом, а не успешное выполнение команды.

## Security boundaries

- OIDC token краткоживущий и выпускается для конкретного workflow run.
- JWT claims нельзя считать доверенными до проверки подписи.
- Локальные секреты и SSH private key не покидают устройство.
- Listener не должен быть напрямую открыт в публичный интернет.
- Команды выполняются с минимальными полномочиями, ограниченным временем и контролируемым выводом.
- Публичный шаблон не содержит персональных значений или рабочих credentials.

## Что ещё требуется реализовать и проверить

- Генерация repository/ref/audience для каждого пользователя.
- Bootstrap на чистом Termux без legacy-конфигурации.
- Поддерживаемый write path для mailbox; GitHub connector ChatGPT может быть read-only.
- Проверка GitHub CLI auth/scopes и безопасная работа с credential.
- Безопасная allowlist-модель команд и явное согласие на рискованные операции.
- Tunnel registration, reconnect и URL rotation.
- Идемпотентность, resume после прерывания и корректная обработка конфликтов.
- Полный end-to-end тест на отдельном тестовом устройстве.
