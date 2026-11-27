# Структура проекта

## Текущая структура

~~~text
ChatGPT-Remote-Hands/
├── .github/workflows/ci.yml
├── docs/
│   ├── ARCHITECTURE.md
│   ├── COMMAND_PROTOCOL.md
│   ├── DECISIONS.md
│   ├── GITHUB_AUTH.md
│   ├── GETTING_STARTED.md
│   ├── INSTALLATION_PLAN.md
│   ├── PROJECT_STRUCTURE.md
│   ├── REFERENCE_ENVIRONMENT.md
│   ├── ROADMAP.md
│   ├── TROUBLESHOOTING.md
│   └── TUNNEL.md
├── scripts/install.sh
├── src/android_remote_bridge/
│   ├── cli.py
│   ├── executor.py
│   ├── oidc.py
│   ├── protocol.py
│   ├── server.py
│   ├── state.py
│   └── tunnel.py
├── templates/operational-repo/
│   ├── .github/workflows/push-bridge.yml
│   └── mailbox/
│       ├── command.json
│       ├── result.json
│       └── tunnel-url.txt
├── tests/
│   ├── test_bridge_runtime.py
│   └── test_protocol.py
├── CHATGPT_PROMPT_RU.md
├── README.md
├── README_EN.md
├── SECURITY.md
└── pyproject.toml
~~~

## Назначение компонентов

| Путь | Назначение |
|---|---|
| src/android_remote_bridge/server.py | loopback listener, OIDC/event validation, GitHub mailbox API, async command worker |
| src/android_remote_bridge/oidc.py | GitHub Actions OIDC JWT verification |
| src/android_remote_bridge/protocol.py | строгая схема shell command envelope |
| src/android_remote_bridge/executor.py | bash -lc execution, timeout, stdout/stderr/exit code |
| src/android_remote_bridge/state.py | persistent sequence, jti replay protection, cached/interrupted result |
| src/android_remote_bridge/cli.py | listener lifecycle: start/stop/status/logs |
| src/android_remote_bridge/tunnel.py | tunnl.gg SSH reverse tunnel, stable URL, reconnect, health keepalive |
| scripts/install.sh | native Termux ARM64 installer draft |
| templates/operational-repo | чистый private mailbox + push-event workflow |
| tests | synthetic unit/integration tests; no personal credentials or mailbox data |

## Данные конкретного пользователя

- Android: local config, replay state, logs, PID, dedicated SSH private key, GitHub CLI credential (managed by gh).
- Private operational repo: workflow, push-bridge/command.json, push-bridge/result.json, push-bridge/tunnel-url.txt.
- GitHub Actions: short-lived OIDC JWT during a workflow run.
- Public repository: generic code, clean templates, documentation and tests only.

## Правила

- Не добавлять реальные credentials, private keys, tunnel URLs, логи и command results в публичный репозиторий.
- Не использовать рабочий private operational repo автора как общий backend.
- Не переиспользовать SSH private key между установками.
- Изменения protocol/server/executor должны сопровождаться тестами и обновлением docs/COMMAND_PROTOCOL.md.
- Bridge работает по push-событиям; не добавлять polling loop для получения команд.
- Shell выполняется в пределах прав Termux app user; write access к private mailbox фактически даёт command authority.
