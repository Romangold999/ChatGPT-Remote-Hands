# Tunnel provider: tunnl.gg (OpenSSH reverse tunnel)

## Схема

Используется tunnl.gg — reverse tunnel поверх OpenSSH. Termux держит исходящее SSH-соединение к proxy.tunnl.gg; сервис направляет входящие HTTPS-запросы на локальный listener 127.0.0.1:18767.

Это та же схема, что в рабочем Termux Push Bridge:
- reverse forwarding: -R 80:127.0.0.1:18767;
- стабильный endpoint: stable@proxy.tunnl.gg;
- отдельный Ed25519-ключ для каждой установки;
- pinned SSH host key;
- reconnect после обрыва;
- URL сохраняется в mailbox/tunnel-url.txt приватного operational repo.

Туннель не опрашивает GitHub. Входящий запрос появляется только после push-события GitHub Actions. Отдельный health ping к собственному /health раз в 55 минут — это keepalive туннеля, а не проверка наличия новых команд.

Официальные материалы:
- https://tunnl.gg/docs
- https://tunnl.gg/stable-urls
- https://tunnl.gg/guides/keep-a-tunnel-running
- https://tunnl.gg/guides/ai-coding-agents

## SSH

~~~bash
ssh -n -T -i ~/.ssh/android-remote-bridge_ed25519 \
  -o IdentitiesOnly=yes \
  -o StrictHostKeyChecking=yes \
  -o UserKnownHostsFile=~/.ssh/known_hosts_android_remote_bridge \
  -o ServerAliveInterval=30 \
  -o ServerAliveCountMax=3 \
  -o ExitOnForwardFailure=yes \
  -R 80:127.0.0.1:18767 stable@proxy.tunnl.gg output=json
~~~

После события tunnel с URL runtime проверяет внешний /health, затем обновляет mailbox/tunnel-url.txt через локальную GitHub CLI авторизацию. Изменение tunnel URL не запускает workflow команд, потому что workflow фильтрует только mailbox/command.json.

## Однократная регистрация ключа

1. Установщик генерирует отдельную пару Ed25519; private key остаётся на Android.
2. Выполняется ssh -t link@proxy.tunnl.gg.
3. Пользователь открывает показанную ссылку, подтверждает регистрацию и возвращается в Termux.
4. Далее используется stable@proxy.tunnl.gg с тем же ключом.

Не переиспользовать SSH-ключ другой установки или рабочего Bridge.

## Host key pinning

- fingerprint: SHA256:5uQ6VobmUpY4wyMmm5jnAwFtt3aX06WYDDM4ER+2WUw;
- known_hosts хранится локально;
- StrictHostKeyChecking=yes;
- неожиданный host key приводит к отказу соединения.

## Reconnect, keepalive и ограничения

Supervisor повторно подключается после разрыва. Отдельный health ping выполняется раз в 55 минут, чтобы бесплатный туннель не простаивал без HTTP-трафика. Это не polling команд или GitHub.

Бесплатный tunnl.gg:
- до 3 одновременных туннелей на IP;
- до 5 GB/сутки;
- idle timeout 2 часа;
- максимальная сессия 24 часа;
- при переподключении stable URL сохраняется;
- во время reconnect несколько секунд запросы могут быть недоступны.

Android может остановить фоновые процессы; 24/7 не гарантируется. Termux:Boot должен оставаться opt-in и не включаться автоматически без согласия.

## Безопасность

- Публичный tunnel URL не является паролем.
- Listener доступен только на loopback.
- Каждый /webhook проверяет короткоживущий GitHub Actions OIDC JWT и точные identity claims.
- /health не раскрывает секреты или конфигурацию.
- Private SSH key и GitHub CLI token не попадают в репозиторий.
- TLS завершается на edge tunnl.gg; это не end-to-end TLS до телефона.

## Управление

~~~bash
android-remote-bridge-tunnel start --config ~/.config/android-remote-bridge/config.json
android-remote-bridge-tunnel status --config ~/.config/android-remote-bridge/config.json
android-remote-bridge-tunnel stop --config ~/.config/android-remote-bridge/config.json
android-remote-bridge-tunnel register --config ~/.config/android-remote-bridge/config.json
~~~
