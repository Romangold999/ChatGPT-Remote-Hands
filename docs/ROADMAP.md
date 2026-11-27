## Этап 1 — минимальный исполняемый Bridge

- [x] Реализовать локальный listener с привязкой только к loopback.
- [x] Реализовать OIDC signature/claims validation через GitHub JWKS.
- [x] Добавить persistent jti replay и sequence state.
- [x] Добавить строгую схему command envelope и лимит размера.
- [x] Добавить начальный allowlist executor без произвольного shell.
- [x] Добавить сохранение последнего terminal result и безопасный ответ на повтор той же команды.
- [x] Добавить unit/integration tests и CI с установкой package dependencies.
- [x] Добавить lifecycle CLI и безопасное управление фоновым процессом.

**Критерий выхода:** локальный Bridge проходит security/integration tests и безопасно обрабатывает повторные запросы и аварийное завершение.

## Этап 2 — приватный operational repository

- [x] Создать чистый template с mailbox и workflow.
- [x] Использовать минимальные OIDC permissions и serialized concurrency.
- [x] Закрепить checkout Action на immutable commit SHA.
- [x] Отправлять structured result обратно в пользовательский mailbox.
- [ ] Автоматически создавать private repo от имени пользователя.
- [ ] Проверять владельца и приватность созданного репозитория.
- [ ] Автоматически настраивать Actions variable для tunnel URL.
- [ ] Протестировать две независимые пользовательские установки.

**Критерий выхода:** пользователь получает собственный private repo, который не пересекается с репозиторием автора или других пользователей.

## Этап 3 — OIDC и защищённый tunnel

- [x] Валидировать GitHub OIDC signature, issuer, audience, repository, ref, timestamps и jti.
- [x] Исследовать tunnl.gg и реализовать stable SSH reverse tunnel для первого бесплатного сценария.
- [x] Реализовать start/stop/status supervisor tunnl.gg, stable URL, reconnect и публикацию Actions variable.
- [ ] Добавить автоматическое восстановление tunnel после остановки Android и безопасную ротацию URL.
- [ ] Проверить end-to-end обмен с реальным tunnel provider.

**Критерий выхода:** listener принимает запросы только от workflow соответствующего private repo.

## Этап 4 — bootstrap и восстановление

- [x] Добавить первый bootstrap draft `scripts/install.sh` для Termux ARM64.
- [ ] Проверить установщик на чистом Termux и довести resume/идемпотентность до release quality.
- [ ] Проверять зависимости и не перезаписывать неизвестные файлы.
- [ ] Использовать GitHub CLI browser/device flow.
- [ ] Создавать private operational repo и загружать только template.
- [ ] Генерировать локальные секреты на устройстве.
- [ ] Реализовать safe resume после прерывания.
- [ ] Добавить Termux:API как optional feature.
- [ ] Добавить Termux:Boot только как отдельный opt-in.

**Критерий выхода:** установка с нуля и продолжение после искусственного прерывания проходят на чистом поддерживаемом устройстве.

## Этап 5 — передача больших данных и release

- [ ] Реализовать chunked transfer с hash/integrity checks, лимитами и TTL.
- [ ] Провести полный end-to-end тест на отдельной тестовой инфраструктуре.
- [ ] Добавить статический анализ и security checks.
- [ ] Опубликовать release notes и проверенную инструкцию установки.

## Не входит в обещания проекта

- Гарантированный uptime 24/7 на Android.
- Неограниченный бесплатный tunnel.
- Постоянная GitHub авторизация без повторных подтверждений.
- Автоматическая запись через read-only GitHub connector.
- Выполнение произвольных команд без ограничений.
