# School Class Manager — контекст для Claude Code

Веб-застосунок на Raspberry Pi 4 (Samba AD DC) для вчителя інформатики: облікові записи учнів, файли (роздатки / здані роботи / папки), стан сервера. Відкривається з ПК класу за `https://dc1.ad.school.lan`, вхід доменним логіном.

Джерело істини для архітектури, API, безпеки й етапів — `docs/plan.md`. Інфраструктура, на яку застосунок спирається, — `docs/deployment.md`. Мокапи (Ant Design) — `docs/mockups.md`. Читай ці три файли перед першою задачею.

## Стек

- Бекенд: .NET 8, ASP.NET Core Minimal API, cookie auth, SSE, OpenAPI (Swashbuckle). Publish `linux-arm64` self-contained.
- Фронтенд: React 18 + TypeScript + Vite, Ant Design 5 (`antd`, `@ant-design/icons`), TanStack Query, react-router, react-i18next (`uk` за замовчуванням). TS-клієнт генерується з OpenAPI (`openapi-typescript`).
- Дані: LDAP (`System.DirectoryServices.Protocols`, `ldapi:///`), процеси через `CliWrap`, файли через `System.IO` у `/srv/data`, SQLite (`Microsoft.Data.Sqlite` + Dapper) для журналу.
- PDF картки: QuestPDF (Community) з вбудованим IBM Plex Sans. CSV: CsvHelper. Логи: Serilog → journald.
- Тести: xUnit + FluentAssertions + NSubstitute; `WebApplicationFactory` для API; Vitest + Testing Library + MSW для SPA.

## Команди

```
dotnet build                 # усе рішення
dotnet test                  # юніт + API-тести (без Pi)
dotnet test --filter Category=Integration   # проти Pi, потрібен SCM_PI_HOST
cd web && npm install && npm run dev        # Vite, проксі /api → https://dc1.ad.school.lan або локальний бекенд
cd web && npm run gen:api    # OpenAPI → src/api/client.ts
cd web && npm test
dotnet publish src/Scm.Api -c Release -r linux-arm64 --self-contained -o out/
```

## Правила

1. Use-case-и в `Scm.Core`; `Process`, LDAP, `System.IO`, SQLite — тільки в `Scm.Infrastructure`. `Scm.Core` не посилається ні на ASP.NET, ні на Infrastructure.
2. Команди на Pi виконуються лише через `SudoRunner` з `ArgumentList` (кожен аргумент окремо). Ніякої конкатенації рядків у shell. Єдині дозволені програми: `/usr/local/sbin/scm-user`, `scm-status`, `scm-logs`, `snap.sh`, `backup.sh`, `systemctl start scm-update.service`.
3. `Login`, `ClassCode`, `StorePath` — value-об'єкти з валідацією в конструкторі. Невалідне значення не доходить ні до обгортки, ні до файлової системи. `StorePath` ніколи не виходить за корінь шари (`Path.GetFullPath` + `StartsWith`).
4. Кожна мутація пише в `IJournal`: `Started` / `Succeeded` / `Failed`, `actor` — з cookie. Паролі ніколи не потрапляють у журнал і логи.
5. Кожен ендпоінт має явну політику `RequireRole("Teacher")` або `"Admin"`; `FallbackPolicy` = 403.
6. Усі рядки UI — через i18n (`web/src/i18n/uk.json`). Компоненти — тільки з antd; не писати власних кнопок, таблиць, модалок.
7. Парсери виводу команд тестуються на фікстурах із `tools/pi-fixtures/`. Нова команда на Pi = нова фікстура в тому ж коміті. Ім'я файлу: `<команда>.<samba-версія>.txt`.
8. Сесія = одна задача з `docs/plan.md` (розділ «План розробки»). Починається з зелених `dotnet test` і `npm test`, закінчується ними ж. Не починати наступний екран, поки поточний не задеплоєно на Pi.

## Структура

Див. `docs/plan.md` → «Структура репозиторію». Коротко: `src/Scm.Core`, `src/Scm.Infrastructure`, `src/Scm.Api`, `web/`, `pi/` (systemd, sudoers, обгортки, TLS, install.sh), `tests/`, `tools/pi-fixtures/`, `docs/`.

## Рішення, які не переглядаються

- `submit` — підпапка на учня (`class/<клас>/submit/<login>/`), її створює GPO logon-скрипт; «хто не здав» = порожня або відсутня підпапка.
- Ролі: Admin (`Domain Admins`) і Teacher (`vchyteli`) з M1. Паролі вчителям скидає тільки Admin (`scm-user --teacher`).
- Кнопка «Оновити» в UI — обов'язкова у v1 (M5).
- Назва: School Class Manager. Ліцензія: MIT.

## Стан

Етап M0 (інфраструктура за `docs/deployment.md`) — виконується вручну. Код починається з M1, сесія 1: рішення, три проєкти, `Scm.Api` з `/healthz`, `web/` з `AppLayout` на статичних даних мокапу, CI зелений.
