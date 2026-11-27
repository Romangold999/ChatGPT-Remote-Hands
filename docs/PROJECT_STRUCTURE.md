# Структура проекта

Этот документ — карта репозитория. Он различает уже существующие материалы и каталоги, которые появятся по мере реализации. Не считайте запланированный путь рабочим компонентом, пока соответствующий код и тесты не добавлены.

## Сейчас в репозитории

```text
Android-Remote-Bridge/
├── README.md
├── CHATGPT_PROMPT_RU.md
├── SECURITY.md
└── docs/
    ├── ARCHITECTURE.md
    ├── COMMAND_PROTOCOL.md
    ├── DECISIONS.md
    ├── GITHUB_AUTH.md
    ├── INSTALLATION_PLAN.md
    ├── PROJECT_STRUCTURE.md
    ├── REFERENCE_ENVIRONMENT.md
    ├── ROADMAP.md
    ├── TROUBLESHOOTING.md
    └── TUNNEL.md
```

## Целевая структура

По мере разработки дерево будет расширяться примерно так:

```text
Android-Remote-Bridge/
├── .github/
│   ├── workflows/          # CI: lint, unit tests, security checks
│   └── ISSUE_TEMPLATE/     # шаблоны безопасных bug reports
├── docs/                   # архитектура, инструкции, решения
├── src/
│   └── android_remote_bridge/
│       ├── bridge/         # локальный HTTP listener и lifecycle
│       ├── auth/           # проверка GitHub OIDC
│       ├── protocol/       # schema, IDs, sequence, mailbox
│       ├── executor/       # allowlist, timeout, output limits
│       └── tunnel/         # адаптеры tunnel providers
├── scripts/                # команды обслуживания и диагностики
├── templates/
│   └── operational-repo/   # чистый шаблон приватного repo пользователя
│       └── .github/workflows/
├── tests/
│   ├── unit/
│   ├── integration/
│   └── fixtures/           # только синтетические тестовые данные
├── install.sh              # bootstrap для Termux (после реализации)
├── pyproject.toml          # Python package/tooling config
├── .gitignore
├── CONTRIBUTING.md
├── SECURITY.md
└── README.md
```

## Назначение каталогов

| Каталог | Что в нём должно быть | Чего там быть не должно |
|---|---|---|
| `.github/workflows/` | CI публичного проекта | пользовательские workflow с реальными endpoint/секретами |
| `src/` | универсальный исходный код Bridge | локальные конфиги и runtime state |
| `scripts/` | универсальные команды установки и обслуживания | экспортированные пользовательские credentials |
| `templates/operational-repo/` | безопасный шаблон приватного репозитория | private keys, PAT, HMAC secrets, tunnel URL |
| `tests/` | автоматические тесты и синтетические fixtures | реальные mailbox, логи и дампы |
| `docs/` | инструкции и архитектурные решения | секреты, персональные адреса и рабочие токены |

## Где будут данные конкретного пользователя

Runtime-данные не хранятся в этом публичном репозитории.

- **На Android:** приватный SSH key, локальные secrets, конфигурация, PID/state и логи. Каталог будет создан установщиком с ограниченными правами.
- **В личном private GitHub repository:** workflow, mailbox, sequence и только необходимые несекретные настройки.
- **В GitHub Actions:** короткоживущий OIDC token на время конкретного запуска.
- **В публичном репозитории:** только общий код и чистые шаблоны.

Каждая установка получает отдельный private repository и отдельную локальную конфигурацию. Нельзя использовать operational repo автора как общий backend.

## Правило обновления карты

При добавлении нового верхнеуровневого каталога или важного файла обновляйте этот документ и таблицу путей в главном README. Не добавляйте сюда фиктивные пути ради красивого дерева.
