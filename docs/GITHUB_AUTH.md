# GitHub auth, CLI, PAT и OIDC

## Разные сущности — не путать

1. GitHub CLI user authentication — сохранённая авторизация пользователя на телефоне.
2. Personal Access Token — credential для GitHub API; classic и fine-grained имеют разные модели permissions/expiry.
3. GitHub Actions OIDC ID token — краткоживущий JWT, выдаваемый workflow на каждый запуск при permission id-token: write.
4. GitHub connector in ChatGPT — отдельная интеграция, может быть read-only и зависит от тарифа/аккаунта.

## Эталонное наблюдение

На reference Termux установлена GitHub CLI 2.105.0. Она авторизована под владельцем эталонного репозитория; scopes в безопасном отчёте: gist, read:org, repo, workflow. Файл авторизации находится в ~/.config/gh/hosts.yml. Сам токен не записан в эту базу.

## Целевой подход

- Проверять `gh auth status`; не выводить credential.
- Проверять текущего пользователя через `gh api user --jq .login`.
- Для новых пользователей использовать официальный интерактивный login/device flow, если поддерживается текущей версией gh.
- Проверить, достаточно ли CLI credential для создания private repo, contents write и workflow operations.
- Не считать, что любой gh auth автоматически выдаёт бессрочный credential. Проверить фактический тип и политику GitHub.
- Fine-grained PAT не является бессрочным; classic PAT без срока может быть запрещён policy и более широк по правам.
- Не запрашивать токен в ChatGPT.
- Для Actions использовать OIDC, а не PAT в workflow.
- В документации указать, что credential может быть отозван GitHub/пользователем/организацией; абсолютной гарантии «навсегда» нет.

## Минимальные Actions permissions

В эталонном workflow:
- contents: read
- id-token: write

Добавлять contents: write только при реальной необходимости. Workflow должен быть ограничен точной branch/path и использовать concurrency lock.
