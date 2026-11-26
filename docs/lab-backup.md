# Ручна резервна копія учнівських папок

Це наступний крок після [перевірки двох учнів](lab-files.md): копія `/srv/school/home` поза VM і перевірка відновлення в окрему папку. Домен AD, його паролі, UID-мапінг та конфігурація сервера до цієї копії **не входять**. Вона призначена для відновлення файлів на тому самому налаштованому сервері. Окремий комплект із доменом та ізольоване випробування його відновлення описані в [lab-domain-recovery.md](lab-domain-recovery.md).

## 1. Підготувати команду в Ubuntu

Із кореня репозиторію на **Mac або в PowerShell Windows-хоста**:

```sh
multipass transfer lab/backup-student-homes.py school-server:/tmp/backup-student-homes.py
multipass exec school-server -- sudo install -m 755 /tmp/backup-student-homes.py /usr/local/sbin/scm-backup-student-homes
```

У домашній VM команду вже встановлено. Скрипт використовує Python 3.12 та GNU tar з Ubuntu 24.04; на Windows-хості встановлювати їх окремо не потрібно.

## 2. Створити копію

Закрити редагування файлів на H: на час ручного копіювання. Скрипт не робить узгоджений знімок активно змінюваної файлової системи.

На **Mac або Windows-хості**:

```sh
multipass exec school-server -- sudo scm-backup-student-homes backup
```

Команда створює унікальний тимчасовий файл у student1, архівує обидві папки та контрольний опис їхнього вмісту й метаданих. Потім видаляє лише власний тестовий файл і відновлює архів в окремий тимчасовий каталог. Перевіряє хеші вмісту, UID/GID, режими доступу, extended attributes (зокрема POSIX ACL і Samba NTACL, якщо вони присутні) та ізоляцію відновлених папок між учнями. Тимчасовий каталог видаляється автоматично. Наявні учнівські файли не видаляються й не перезаписуються.

Очікується:

```text
RESTORE_OK: contents, UID/GID, modes, xattrs, pupil isolation.
ARCHIVE=/home/ubuntu/school-homes-<UTC-time>-<unique-id>.tar.gz
SHA256=<checksum>
```

Параметри `--acls`, `--xattrs`, `--xattrs-include=*`, `--numeric-owner` зберігають права й ідентифікатори. Для відновлення всіх просторів extended attributes потрібен явний `--xattrs-include=*`; див. [GNU tar](https://www.gnu.org/software/tar/manual/tar.html).

## 3. Зберегти поза VM

Нижче замінити `ARCHIVE_NAME` на ім'я файла з рядка `ARCHIVE`, без каталогу `/home/ubuntu/`.

На **Mac**, у корені репозиторію:

```sh
mkdir -p .local-backups
chmod 700 .local-backups
multipass transfer school-server:/home/ubuntu/ARCHIVE_NAME .local-backups/ARCHIVE_NAME
chmod 600 .local-backups/ARCHIVE_NAME
shasum -a 256 .local-backups/ARCHIVE_NAME
```

На **Windows-хості**, у PowerShell у корені репозиторію:

```powershell
New-Item -ItemType Directory -Force .local-backups | Out-Null
multipass transfer school-server:/home/ubuntu/ARCHIVE_NAME .local-backups/ARCHIVE_NAME
Get-FileHash .local-backups/ARCHIVE_NAME -Algorithm SHA256
```

Хеш має збігатися з `SHA256`, надрукованим сервером. Використовувати особисту папку адміністратора хоста з обмеженим доступом; архів містить учнівські файли без шифрування. `.local-backups/` виключено з Git, але це саме по собі не обмежує доступ інших локальних користувачів Windows. Права цільової папки шкільного хоста ще потрібно перевірити на місці.

## 4. Перевірити саме копію з хоста

На **Mac або Windows-хості**:

```sh
multipass transfer .local-backups/ARCHIVE_NAME school-server:/home/ubuntu/restore-ARCHIVE_NAME
multipass exec school-server -- sudo scm-backup-student-homes verify /home/ubuntu/restore-ARCHIVE_NAME
```

Очікується `RESTORE_OK`. Команда розпаковує лише в тимчасовий каталог, перевіряє вміст і права та прибирає його. Це перевірка відновлюваності, а не перезапис робочих папок. Перевіряти лише власні архіви з цієї процедури.

Після успішного порівняння хешів і `RESTORE_OK` можна видалити два дублікати з VM, зберігши копію на хості:

```sh
multipass exec school-server -- rm /home/ubuntu/ARCHIVE_NAME /home/ubuntu/restore-ARCHIVE_NAME
```

Для реального відновлення окремої втраченої роботи спочатку вибрати потрібний архів і файл, розпакувати в окремий каталог, перевірити та скопіювати до учнівської папки з відповідними метаданими. Не розпаковувати весь архів поверх робочих папок: це може перезаписати новіші роботи.

## Перевірено 2026-11-25

- Створено `school-homes-20261125T195506Z-f1b1c4edde2e.tar.gz` та збережено на Mac у `.local-backups/` в корені репозиторію, каталог 0700, файл 0600.
- SHA-256 у VM та на Mac збігся: `2235e0d2570e57a2a57625988e6dfe39b114f4646dc069cd05414a2799802ee3`.
- Видалений тестовий файл відновився в окремій папці з правильним вмістом, власником, правами та тестовим extended attribute.
- Копію з Mac повернуто у VM; повторне відновлення, порівняння всього вмісту й метаданих та перевірка ізоляції дали `RESTORE_OK`.
- Робочі файли учнів залишено на місці. Тимчасові архіви у VM прибрано; перевірена копія зберігається на Mac.
- Це ручна копія файлів. Розклад, термін зберігання та копія на іншому фізичному носії ще не налаштовані. Окрему копію домену та серверну перевірку її відновлення вже виконано — [lab-domain-recovery.md](lab-domain-recovery.md). Копія на тому самому Mac переживе втрату VM, але не втрату диска Mac.
- Команди Windows-хоста підготовлено; їх виконання на шкільному ноутбуці ще не перевірено.
