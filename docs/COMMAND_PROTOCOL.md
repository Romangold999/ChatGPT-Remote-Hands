# Протокол push-mailbox (совместим с Termux Push Bridge)

## Принцип работы

Bridge работает по push-событиям. Termux НЕ опрашивает GitHub и не запрашивает новые команды по таймеру.

1. GPT записывает push-bridge/command.json со статусом ready в личный private operational repository.
2. Push в ветке push-bridge по пути push-bridge/command.json запускает GitHub Actions.
3. Workflow checkout-ит точный commit SHA, получает короткоживущий GitHub Actions OIDC JWT с audience termux-push-bridge и отправляет на туннель только событие: repository, ref, after (SHA коммита), timestamp.
4. Termux проверяет JWT и событие, затем сам один раз получает command.json из GitHub по точному SHA события.
5. Termux выполняет bash -lc с командой в домашнем каталоге Termux с заданным timeout.
6. Termux публикует push-bridge/result.json через GitHub Contents API и меняет статус команды с ready на конечный статус.
7. GPT читает result.json, проверяет id и sequence, анализирует stdout/stderr/exit code и при необходимости отправляет следующую команду новым push-событием.

Webhook отвечает 202 Accepted сразу после постановки команды в локальный worker. Это означает только принятие события, а не завершение команды. GitHub Actions не ждёт shell-команду и не публикует результат вместо Termux.

## Файлы приватного operational repository

- push-bridge/command.json — входящая команда и её статус.
- push-bridge/result.json — результат последней команды.
- push-bridge/tunnel-url.txt — текущий стабильный HTTPS endpoint tunnl.gg.
- .github/workflows/push-bridge.yml — push-triggered event dispatcher.

## Формат команды v1

~~~json
{
  "version": 1,
  "id": "unique-command-id-001",
  "sequence": 1,
  "status": "ready",
  "operation": "shell",
  "approval": "not_required",
  "timeout_seconds": 300,
  "command": "pwd && ls -la"
}
~~~

Правила:
- version: строго integer 1.
- id: непустая строка до 120 символов, только буквы, цифры, _, ., :, -.
- sequence: положительное целое число, строго следующее после последнего выполненного.
- status: новая команда должна иметь значение ready.
- operation: строго shell.
- command: полноценная shell-команда для Bash, не более 20 000 символов.
- timeout_seconds: от 1 до 3600, по умолчанию 300.
- approval: not_required или approved. Это декларация состояния согласования, а не самостоятельный механизм подтверждения.

## Формат результата

~~~json
{
  "version": 1,
  "id": "unique-command-id-001",
  "sequence": 1,
  "status": "completed",
  "started_at": "2026-01-01T12:00:00+00:00",
  "finished_at": "2026-01-01T12:00:01+00:00",
  "exit_code": 0,
  "stdout": "…",
  "stderr": "",
  "error": null
}
~~~

status может быть completed, failed, timeout или error. Stdout и stderr ограничиваются последними 100 000 символами каждый. Для передачи больших файлов нужен отдельный потоковый протокол; не помещай бинарные файлы в JSON mailbox.

## Аутентификация и защита от повторов

Listener проверяет:
1. RS256-подпись JWT по опубликованному GitHub JWKS.
2. Issuer https://token.actions.githubusercontent.com.
3. Audience termux-push-bridge.
4. Точные claims repository, ref и event_name=push.
5. exp, iat, nbf и обязательный jti.
6. Поля события: repository/ref совпадают с локальным конфигом, SHA имеет формат 40 hex, timestamp не старше часа.

Локальный persistent state защищает от повторного jti, повторного ID с другим payload и неправильного sequence. Команды сериализуются: пока выполняется одна команда, следующая получает HTTP 409. Повтор того же ID/sequence/payload после сохранения результата не запускает shell повторно; можно повторно опубликовать сохранённый результат.

## GitHub credentials

Actions нужен только contents: read для checkout private repo и id-token: write для короткоживущего OIDC JWT. Termux использует локальную авторизацию GitHub CLI (gh auth token) для чтения команды и записи результата/ack в private repo. Токен не передаётся в webhook, не сохраняется в конфиге Bridge и не печатается в логах. GitHub CLI должен иметь Contents read/write для operational repo.

## Граница доверия

Полноценный shell — это реальное выполнение команд от имени пользователя Termux. Любой, кто может записать push-bridge/command.json в private operational repo, получает возможность запускать команды на устройстве. Поэтому:
- operational repo обязан быть private;
- доступ на запись выдавай только доверенному пользователю/интеграции;
- не публикуй tunnel URL как секрет — безопасность обеспечивает OIDC;
- не помещай команды с секретами в публичные issue/PR;
- не запускай опасные или разрушающие действия без отдельного согласия пользователя.

Listener слушает только 127.0.0.1:18767. Внешний доступ идёт через tunnl.gg reverse SSH tunnel. Никакого polling GitHub со стороны Termux нет.
