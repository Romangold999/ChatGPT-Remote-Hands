# ChatGPT Remote Hands

<p align="center">
  <strong>Дай ChatGPT руки для работы с твоим Android-устройством.</strong><br>
  <sub>Персональный мост между ChatGPT и Android через Termux.</sub>
</p>

<p align="center">
  <a href="README_EN.md">English version</a>
</p>

<p align="center">
  <img alt="Platform" src="https://img.shields.io/badge/platform-Android%20%7C%20Termux-3DDC84?logo=android&logoColor=white">
  <img alt="Integration" src="https://img.shields.io/badge/integration-ChatGPT-10A37F">
  <img alt="Status" src="https://img.shields.io/badge/status-experimental-orange">
</p>

> **Статус: экспериментальный проект.** Архитектура push-bridge и shell executor реализуются по эталону рабочего Termux Push Bridge. До готового релиза ещё нужны CI, чистая установка на Android и полный end-to-end тест на отдельной установке. Не запускай экспериментальный установщик на основном рабочем окружении.

## Что это

ChatGPT Remote Hands — независимый open-source проект, который связывает ChatGPT с личным Android-устройством через Termux, GitHub Actions и reverse SSH tunnel tunnl.gg.

Bridge работает как полноценный исполнитель shell-команд от имени пользователя Termux. Команды могут запускать доступные в Termux программы, работать с файлами и выполнять системные инструменты в пределах прав Android-приложения Termux. Это не root и не удалённый рабочий стол.

## Как это работает

1. GPT записывает команду в push-bridge/command.json личного приватного GitHub-репозитория.
2. Push запускает GitHub Actions. Workflow получает короткоживущий OIDC JWT и отправляет через HTTPS-туннель в Termux только событие с repository, ref, commit SHA и timestamp.
3. Termux проверяет подпись и claims, затем забирает команду из GitHub по точному SHA и выполняет bash -lc с timeout.
4. Сам Termux записывает stdout, stderr, exit code и статус в push-bridge/result.json и подтверждает команду.
5. GPT читает результат и при необходимости отправляет следующую команду новым push-событием.

**Termux не опрашивает GitHub и не делает запросы за заданиями каждые две секунды.** Новая команда приходит только по событию GitHub Actions через tunnl.gg. HTTP 202 означает, что событие принято, а не что команда уже завершилась.

## Возможности

- Полноценное исполнение Bash-команд в окружении Termux.
- stdout, stderr, exit code, timeout до 3600 секунд.
- Работа с файлами, каталогами, Git, Python, Node.js и другими установленными в Termux инструментами.
- GitHub Actions OIDC: RS256, issuer, audience, repository, branch/ref, event_name, временные claims и jti replay protection.
- Получение команды по точному SHA события; локальная защита от повторов и последовательностей.
- Публикация результата самим Termux в private mailbox.
- Стабильный tunnl.gg URL, reconnect, SSH keepalive и health ping.
- Отдельный приватный operational repo и отдельный Ed25519 SSH key для каждой установки.
- Установщик для native Termux ARM64.

## Безопасность

Полный shell означает реальную власть над файлами и программами в пределах Termux. Поэтому приватный operational repository должен оставаться приватным: тот, кто имеет право записи в push-bridge/command.json, фактически получает право выполнять команды на устройстве.

GitHub Actions только передаёт событие. Для чтения команды и публикации результата Termux использует локальную авторизацию GitHub CLI. Долгоживущий GitHub token не помещается в конфигурацию Bridge, webhook или публичный репозиторий. OIDC JWT краткоживущий и проверяется на каждом входящем событии.

Установка создаёт собственный SSH-ключ tunnl.gg. Private key остаётся на Android. Не переиспользуй ключ от другой установки или рабочего Bridge.

Подробности: [SECURITY.md](SECURITY.md), [протокол команд](docs/COMMAND_PROTOCOL.md), [туннель](docs/TUNNEL.md).

## Перед установкой

Проект пока экспериментальный. Перед публичным релизом нужно подтвердить:
- clean install на чистом Termux ARM64;
- GitHub browser authorization и создание private operational repo;
- регистрацию отдельного tunnl.gg ключа;
- полный цикл команда → push event → Termux → result mailbox;
- timeout, non-zero exit, replay protection и восстановление после обрыва;
- корректное управление фоновыми процессами Android.

Инструкция: [docs/GETTING_STARTED.md](docs/GETTING_STARTED.md).

## Ограничения

- Команды выполняются с правами приложения Termux; root-доступ не предоставляется.
- Android может останавливать фоновые процессы, поэтому 24/7 не гарантируется.
- Бесплатный tunnl.gg имеет лимиты на трафик, простой и длительность сессии.
- tunnl.gg завершает TLS на своей edge-инфраструктуре; это не end-to-end шифрование до телефона.
- Для полноценной работы ChatGPT нужен канал, способный записать команду в private repo и прочитать результат. GitHub connector может быть read-only.
- Успешный запуск workflow или HTTP 202 не подтверждает выполнение. Проверяй result.json.

## Независимость проекта

Это независимый open-source проект. **Он не является официальным продуктом OpenAI и не одобрен OpenAI.**

---

<p align="center">
  <sub>Твой Android, твой Bridge, твои ключи, твои правила.</sub>
</p>
