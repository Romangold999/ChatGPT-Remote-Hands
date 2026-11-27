# Tunnel provider: tunnl.gg (OpenSSH reverse tunnel)

## Выбранная схема

Используется tunnl.gg — reverse tunnel поверх обычного OpenSSH. На Android не нужен отдельный агент: телефон сам открывает исходящее SSH-соединение к proxy.tunnl.gg, а сервис выдаёт публичный HTTPS-адрес и передаёт запросы на локальный listener 127.0.0.1:18766.

Это та же схема, что используется в рабочем Termux Push Bridge:
- SSH reverse forwarding: -R 80:127.0.0.1:18766;
- стабильный адрес: stable@proxy.tunnl.gg;
- отдельный Ed25519 key на устройство/установку;
- автоматическое переподключение после обрыва;
- pinned SSH host key;
- Actions variable BRIDGE_TUNNEL_URL в личном private operational repo.

Официальные материалы: https://tunnl.gg/docs, https://tunnl.gg/stable-urls, https://tunnl.gg/guides/keep-a-tunnel-running, https://tunnl.gg/guides/ai-coding-agents.

## Команда подключения

ssh -n -T -i ~/.ssh/android-remote-bridge_ed25519 -o IdentitiesOnly=yes -o StrictHostKeyChecking=yes -o UserKnownHostsFile=~/.ssh/known_hosts_android_remote_bridge -o ServerAliveInterval=30 -o ServerAliveCountMax=3 -o ExitOnForwardFailure=yes -R 80:127.0.0.1:18766 stable@proxy.tunnl.gg output=json

В JSON-режиме первая строка — событие tunnel с полем url. Runtime проверяет внешний /health, затем записывает URL в Actions variable личного private repo. Supervisor повторно подключается через 5 секунд после обрыва. При использовании того же зарегистрированного ключа stable URL сохраняется.

## Однократная регистрация ключа

Для стабильного адреса tunnl.gg требует зарегистрировать публичный SSH-ключ в бесплатном аккаунте:
1. Установщик создаёт отдельную пару Ed25519 на телефоне; private key остаётся локально.
2. Запускается ssh -t link@proxy.tunnl.gg с этим ключом.
3. Пользователь открывает показанную ссылку, завершает регистрацию ключа и возвращается в Termux.
4. После этого используется stable@proxy.tunnl.gg.

Для существующей рабочей установки можно использовать путь к уже зарегистрированному личному ключу, если он найден локально. Сам ключ не читается в чат и не копируется в публичный репозиторий.

## Проверка host key

Host key закреплён в known_hosts по опубликованному tunnl.gg ED25519 ключу:
- fingerprint: SHA256:5uQ6VobmUpY4wyMmm5jnAwFtt3aX06WYDDM4ER+2WUw;
- запись хранится локально;
- StrictHostKeyChecking=yes;
- смена host key приводит к отказу соединения, а не к автоматическому принятию нового ключа.

## Поддержание соединения и ограничения

Supervisor автоматически переподключает SSH после разрыва. Он также обращается к собственному /health через туннель раз в 55 минут, чтобы бесплатный туннель не простаивал без HTTP-трафика. Ограничения бесплатного tunnl.gg:
- до 3 одновременных туннелей на IP;
- до 5 GB передачи в сутки;
- закрытие после 2 часов бездействия;
- максимальная продолжительность одной сессии — 24 часа;
- после 24 часов supervisor подключается заново с тем же stable URL;
- во время переподключения несколько секунд запросы могут быть недоступны.

Android может остановить фоновые процессы; непрерывная работа 24/7 не гарантируется. Termux:Boot остаётся необязательным и не включается без отдельного согласия.

## Безопасность и приватность

- Публичный URL не является паролем.
- Listener слушает только 127.0.0.1:18766.
- Каждый webhook проверяет краткоживущий GitHub Actions OIDC JWT и точные claims repository/ref.
- Внешний GET /health возвращает только {"status":"ok"}.
- SSH private key и локальная конфигурация не попадают в operational repo или публичный проект.
- TLS завершается на edge tunnl.gg; трафик не следует считать end-to-end зашифрованным до телефона. Не публиковать через этот туннель посторонние чувствительные сервисы.
- Browser warning tunnl.gg показывается браузерам; GitHub webhook/curl-запросы идут напрямую.

## Команды управления

android-remote-bridge-tunnel start --config ~/.config/android-remote-bridge/config.json
android-remote-bridge-tunnel status --config ~/.config/android-remote-bridge/config.json
android-remote-bridge-tunnel stop --config ~/.config/android-remote-bridge/config.json
android-remote-bridge-tunnel register --config ~/.config/android-remote-bridge/config.json
