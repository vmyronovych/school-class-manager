# School Class Manager — робочий контекст

## Чинний стан і пріоритети

Починати з [README](README.md) і [checkpoint 2026-11-26](docs/checkpoint-2026-11-26.md). Вони та `docs/lab-*.md` мають пріоритет над архівним Pi-планом у `docs/plan.md`, `docs/deployment.md`, мокапами й `pi/`.

Основна гілка — `main`. PR #3 (`m1/s2a-login-format`, d9872ed) і #4 (`classroom-server-infrastructure`, 5b30382) замінені перевіреним напрямом без злиття; гілки зберігаються для довідки. Не зливати автоматично старі припущення про формати логінів, mandatory profiles чи Vagrant.

Перевірено:

- MacBook M1 16 GB → Multipass 1.17.2 → Ubuntu 24.04 ARM64 `school-server` (2 CPU, 4 GB RAM, 30 GB диск). LAN `192.168.1.176`, домен `school.test` / `SCHOOL`, Samba 4.19.5. Домен уже існує; повторний provisioning не запускати.
- Фізичний Windows 10 Pro Education `DESKTOP-N8KR882` приєднано до домену, secure channel працює. Student1/student2 входили, записували файли на H:, доступ до чужих папок відхилено.
- Жива панель `https://school-server.school.test:8443` / `https://192.168.1.176:8443`, systemd `scm-panel`. Вхід із Mac, створення vmyronovych, пароль і вхід цього учня у Windows підтверджені користувачем. Перегляд папок і завантаження через панель працюють.
- GPO `SCM - Student Documents and Desktop`, GUID `{7160EA2E-5F7D-492A-B06F-D9C1F8F21034}`, тільки scm-students. Заголовок fdeploy1.ini **Version=100**, не VersionNumber: стара форма давала event 511. Встановлена user revision 2 (131072). Після виправлення користувач підтвердив UNC MyDocuments і появу Documents/Desktop для vmyronovych та student2. Деталі в docs/lab-folder-redirection.md.
- Ручні копії та ізольоване відновлення старого комплекту Samba пройдені. `school-recovery` зупинена, не підключати її до робочої LAN. TLS/стан панелі й аудит ще не включені в повне перевірене відновлення; автоматичні копії не налаштовані.

Наступний узгоджений напрям — Shared PC через PowerShell на тестовому Windows-клієнті, потім шкільний Windows-хост і Ubuntu x64. Shared PC поки не реалізований; на Windows-хості серверної VM його не вмикати. Не видаляти реальні локальні профілі без інвентаризації й узгодження конкретного охоплення. Масові операції/класи/нові екрани поза поточним етапом.

## Повторюваність та приватні дані

- Кожну дію має бути можливо повторити на шкільному Windows-хості. Документувати місце виконання: Mac, PowerShell хоста, Ubuntu VM або Windows-клієнт. Перевірене лише на Mac не називати перевіреним на Windows.
- Скрипти lab/ поки прив'язані до тестових імен, адрес та початкових student1/student2. Перед школою потрібна конфігурація та окрема перевірка Ethernet/віртуалізації. Не переносити ARM64-диск на x64.
- Паролі задає користувач приватно; не запитувати їх у чаті. Не включати секрети у argv, журнали чи Git. `.local-backups/` містить приватні дані, не комітити. `web/.vite/` — локальний кеш, не видаляти заради чистого git status.
- Поточні паролі реальних акаунтів не змінювати для тестів. Живі smoke-тести створюють окремі тимчасові акаунти й прибирають тільки свої дані.

## Архітектура поточної панелі

- ASP.NET Core 8 / React 18 / TypeScript / Ant Design 5. Core — моделі/порти, Infrastructure — процеси, API — HTTP. API-типи генеруються зі Swagger.
- `IStudentAdministration`, `IStudentFiles` → `SambaStudentAdministration` → `SudoRunner` → `/usr/local/sbin/scm-directory` без аргументів. JSON і секрети через stdin, Python `-I`, пароль відсутній в argv. Старий `scm-user` не встановлено для живої панелі.
- Вебсервіс працює як scm; root bridge перевіряє активність, SID і групу вчителя на кожній операції. Вхід — Kerberos із LDAP SASL sealing (`Credentials.guess(lp)`, MUST_USE_KERBEROS).
- Учні: scm-students; учителі: vchyteli; адміністратори: Domain Admins. Роль визначає членство, а не формат імені. AccountName нормалізує регістр; старі Login/ClassCode лишаються поза живим шляхом.
- Нові учні отримують H: `\\school-server.school.test\pupils`, share path `/srv/school/home/%U`. У перенаправленнях не додавати зайвий `%USERNAME%`. `csc policy = disable` на pupils/student1/student2, AppData/Downloads лишаються локальними.
- Паролі учнів за явним вибором користувача: 7 символів, два склади + три цифри (напр. Mepa234, лише приклад). Доменну складність не вимикати. Обмеження генератора описано в docs/lab-panel.md; не використовувати його для адмінів.
- Cookie Secure/HttpOnly/SameSiteStrict, 20 хвилин, POST із CSRF, обмеження спроб входу. Аудит Started/Succeeded/Failed — root-only `/var/lib/scm-directory/journal.sqlite3`, без паролів.
- Учитель бачить усіх звичайних учнів, не лише клас. Файли тільки для читання: до 20 МіБ, 2000 записів у папці, без symlink/hardlink/special files; перевірка O_NOFOLLOW для кожної складової шляху.
- Зміна пароля не завершує існуючих Windows/SMB-сеансів; NTLM може тимчасово приймати попередній пароль.

## Робочі правила

- Бізнес-порти в Scm.Core; Process/LDAP/IO тільки Infrastructure або вузький перевірений root bridge. Core не залежить від ASP.NET/Infrastructure.
- Команди через ArgumentList, без shell-конкатенації. Валідація входу до виклику bridge; авторизація повторно всередині bridge.
- Усі рядки UI через i18n; компоненти Ant Design. Не показувати мок-дані як живий стан. Секрети прибирати після закриття модального вікна.
- Перевіряти зміни відповідними тестами; серверні тести не доводять застосування політики Windows. `samba-tool gpo list` перевіряє Read, не Apply Group Policy.
- Нові відтворювані фікстури не мають містити реальних секретів чи учнівських файлів.

## Перевірки та збірка

```sh
dotnet test
npm --prefix web ci
npm --prefix web test -- --run
npm --prefix web run build
python3 lab/validate.py
dotnet publish src/Scm.Api -c Release -r linux-arm64 --self-contained -o out/panel-arm64
# Для Ubuntu x64 — окремий каталог і -r linux-x64.
```

Локально пройдено 109 .NET, 6 React та 4 Python-тести. CI додатково перевіряє синтаксис lab/ і збирає ARM64/x64 артефакти. Збірка x64 не означає перевіреного запуску на шкільному хості. Стан npm audit та інші відкриті межі — у checkpoint.
