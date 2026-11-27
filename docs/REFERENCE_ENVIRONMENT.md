# Тестовая среда и совместимость

Этот документ задаёт категории проверок для разработки. Он намеренно не публикует характеристики конкретного пользовательского устройства, аккаунты, локальные пути, адреса туннелей или значения конфигурации.

## Целевой профиль первой версии

- Android.
- Termux (нативная среда, не Ubuntu/proot по умолчанию).
- ARM64 / aarch64.
- Python 3, Git, OpenSSH, curl и jq.
- GitHub CLI, если поддерживаемая сборка доступна для целевой среды.
- Опциональные Android plugin apps: Termux:API и Termux:Boot.

## Termux и plugin compatibility

- Termux — обязательный Android app.
- Termux:API — дополнительный Android app. Если используются его функции, также установить CLI package `termux-api` через Termux package manager.
- Termux:Boot — дополнительный Android app для пользовательских startup scripts после reboot; не является обязательным для базового Bridge.
- APK Termux и всех plugins должны иметь совместимую подпись от одного источника. Смешивать F-Droid и GitHub builds нельзя.
- Для API-функций тестировать Android runtime permissions и корректную обработку отказа пользователя.
- Для Boot тестировать first-launch registration, reboot, запуск скрипта и восстановление после Android force-stop/battery restrictions.

## Что проверять на каждом устройстве

- Версию Android и ABI.
- Версию Termux и доступность пакетного менеджера.
- Источник и совместимость подписей установленных plugin apps.
- Наличие и версии runtime dependencies.
- Наличие Termux:API app + `termux-api` CLI package, если API features включены.
- Наличие Termux:Boot только если пользователь включил boot integration.
- Возможность GitHub CLI browser/device authentication.
- Доступность GitHub API и Git operations.
- Возможность запускать локальный listener и reverse tunnel.
- Поведение фонового процесса при выключенном экране и энергосбережении.
- Корректную остановку и повторный запуск.

## Принцип минимальных зависимостей

Не устанавливать Termux:API и Termux:Boot как безусловные зависимости базового Bridge. Сначала определять, нужны ли функции Android API и хочет ли пользователь автозапуск. APK-плагины — отдельные Android приложения; одноимённые CLI-пакеты внутри Termux не заменяют APK.

## Матрица тестирования

Проверить как минимум:
- чистую установку на ARM64;
- повторный запуск bootstrap;
- восстановление после прерывания;
- GitHub auth revoke/re-login;
- tunnel reconnect и смену URL;
- OIDC success и отрицательные проверки claims;
- replay и повторную доставку;
- oversized payload и chunked transfer;
- timeout, non-zero exit и ограничение вывода;
- Android API permission denied/granted;
- Termux:Boot opt-in, first launch и reboot;
- остановку процесса Android системой.
