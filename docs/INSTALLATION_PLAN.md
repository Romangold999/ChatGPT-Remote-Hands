# План универсальной установки

Документ описывает целевой сценарий. Это не готовые команды установки.

## Предварительные требования

- Android с поддерживаемой архитектурой (первый целевой профиль — ARM64).
- Termux из поддерживаемого источника.
- GitHub account.
- AI assistant с каналом чтения и отдельным подтверждённым write-capable каналом для mailbox.
- Сеть, позволяющая подключаться к GitHub и выбранному tunnel provider.

## Bootstrap

1. Проверить Termux environment, Android release, ABI и доступ к хранилищу.
2. Установить только минимальные пакеты через `pkg`: Python, Git, OpenSSH, curl, jq и другие строго необходимые зависимости.
3. Проверить доступность GitHub CLI в Termux и установить поддерживаемым способом.
4. Выполнить GitHub CLI browser/device authorization; не передавать credential в чат.
5. Проверить auth status и необходимые scopes без вывода токена.
6. Создать уникальный private repository и проверить visibility/default branch.
7. Загрузить operational template в пользовательский private repo.
8. Сгенерировать индивидуальные config, audience/repository/ref values и SSH key.
9. Зарегистрировать public key у выбранного tunnel provider; сохранить host fingerprint и known_hosts.
10. Запустить локальный listener и tunnel supervisor.
11. Создать Actions workflow с минимальными permissions и закреплёнными Actions.
12. Выполнить тестовую команду с безопасным эффектом.
13. Проверить result mailbox и завершить настройку.

## Idempotency / resume

- Повторный запуск не должен терять настройки.
- Каждый этап фиксирует completion marker в локальном state file без секретов.
- Перед изменением существующего файла — backup.
- При прерывании продолжать с последнего подтверждённого этапа.
- Не перезаписывать чужой repository или Termux конфигурацию.
- Не включать Termux:Boot автоматически без отдельного согласия.

## Авторизация

Предпочтительно использовать сохранённую GitHub CLI auth. Не создавать PAT только ради обхода браузера. Проверить, какие scopes нужны для создания repository, записи contents и workflow. Разделять user auth и Actions OIDC. Не обещать бессрочную авторизацию.

## Tunnel

Сравнить доступные tunnel providers по поддержке SSH reverse forwarding, host key verification, стабильности URL, ограничениям бесплатного плана и условиям использования. Не привязывать универсальный установщик к одному провайдеру до проверки. URL может изменяться; updater должен безопасно обновлять приватную конфигурацию.

## Восстановление

- GitHub auth invalid: предложить повторную авторизацию по запросу пользователя.
- Tunnel disconnected: проверить tunnel process, URL rotation и health.
- Bridge stopped: проверить PID/log/health, затем предложить запуск.
- Actions failure: изучить точные run/job/step logs.
- OIDC rejection: проверить issuer/audience/repo/ref/time/JWKS.
- Mailbox stuck: проверить id/sequence/status и не перезаписывать активную команду.
