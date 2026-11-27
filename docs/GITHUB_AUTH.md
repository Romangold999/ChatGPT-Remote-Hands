# GitHub auth, CLI и OIDC

## Это разные механизмы

1. GitHub CLI authorization — локальная авторизация пользователя в Termux.
2. GitHub API credential — токен, которым GitHub CLI подписывает API-запросы.
3. GitHub Actions OIDC ID token — короткоживущий JWT для аутентификации входящего push-события перед Bridge.
4. GitHub connector in ChatGPT — отдельная интеграция; она может быть read-only и не обязательно умеет записывать команды.

## Push Bridge flow

GitHub Actions не получает и не передаёт shell-команду в webhook. Он отправляет только event metadata: repository, ref, after commit SHA, timestamp.

Termux:
- проверяет OIDC JWT;
- использует локальную авторизацию GitHub CLI через gh auth token;
- читает mailbox/command.json по точному commit SHA;
- выполняет команду;
- записывает mailbox/result.json и подтверждает command status через GitHub Contents API.

GitHub CLI credential не помещается в Bridge config, webhook, workflow output или logs. Он не передаётся в ChatGPT.

## Установка и права

Installer запускает gh auth login при отсутствии сессии. После авторизации нужно проверить gh auth status и текущего владельца через gh api user.

Локальный GitHub CLI credential должен иметь Contents read/write для отдельного private operational repository. Если используются fine-grained permissions, предоставь доступ только к созданному operational repo и Contents read/write. Не выдавай лишние права без необходимости.

## GitHub Actions permissions

Workflow использует минимальные permissions:
- contents: read — checkout private operational repository;
- id-token: write — получение краткоживущего OIDC JWT.

Actions не публикует result.json. Результат публикует сам Termux через локальный GitHub CLI credential.

## OIDC validation

Bridge требует:
- issuer https://token.actions.githubusercontent.com;
- audience termux-push-bridge;
- точный repository;
- точный ref refs/heads/main;
- event_name=push;
- exp, iat, nbf и jti;
- подпись RS256 по GitHub JWKS.

Не путать OIDC с gh login. OIDC JWT краткоживущий и запрашивается заново на каждый workflow run. GitHub CLI credential — локальная пользовательская авторизация и может быть отозвана или истечь.

## ChatGPT integration

Сам GitHub connector может иметь только read permissions. Для работы нужен реальный канал, который может:
- записать новую команду в mailbox/command.json;
- прочитать mailbox/result.json;
- сверить ID и sequence перед отправкой следующей команды.

Наличие read-only GitHub connector не означает, что ChatGPT может управлять Bridge.
