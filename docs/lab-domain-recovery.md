# Копія домену й ізольована перевірка відновлення

Продовження [копіювання учнівських файлів](lab-backup.md). Резервна копія тепер містить також домен Samba: облікові записи, їхні секрети, DNS, SYSVOL та локальний UID-мапінг. Це комплект даних і конфігурації для відновлення, а не образ усього диска Ubuntu.

## Створення копії на робочому сервері

У терміналі **Mac або PowerShell Windows-хоста**, з кореня репозиторію:

```sh
multipass transfer lab/backup-domain.py school-server:/tmp/backup-domain.py
multipass exec school-server -- sudo install -m 755 /tmp/backup-domain.py /usr/local/sbin/scm-backup-domain
multipass exec school-server -- sudo scm-backup-domain
```

Потрібна вже встановлена команда `scm-backup-student-homes` із попереднього етапу. На час копіювання закрити редагування учнівських файлів і не змінювати облікові записи. Штатна команда `samba-tool domain backup offline` використовує блокування баз; слово `offline` не вимагає вимкнення запущеної Samba в цій версії. Файлова копія та копія AD створюються послідовно, це не спільний атомарний знімок. Довідка — [samba-tool](https://www.samba.org/samba/docs/current/man-html/samba-tool.8.html), фактичні параметри також перевірено через `--help` установленої Samba 4.19.5.

Команда перевіряє базу AD, створює штатний архів Samba, копію папок учнів із перевіркою відновлення, копію конфігурації та опис SID/UID/версій. Друкує лише шлях `DOMAIN_BUNDLE` та `SHA256`, без паролів.

Склад комплекту:

- `domain.tar.bz2` — штатний архів домену, зокрема `sam.ldb`, секрети, `idmap.ldb`, SYSVOL і конфігурація Samba.
- `homes.tar.gz` — файли двох учнів та опис вмісту й метаданих.
- `host-config/` — Samba, Kerberos, NSS, hosts, resolver, Netplan та шаблон hosts для cloud-init. Ці файли зберігаються як довідка; їх не слід автоматично переносити на іншу мережу чи інший хост.
- `inventory.json` — SID домену й акаунтів, атрибути домашніх папок, UID/GID та версії пакетів. Для поточної лабораторії явно перевіряються student1, student2 і DESKTOP-N8KR882$.

Скопіювати архів на хост за процедурою з [lab-backup.md](lab-backup.md), використовуючи надруковане ім'я `school-domain-…tar.gz`, та порівняти SHA-256. На Mac каталог `.local-backups` має права 0700, архів — 0600. Архів містить секрети домену, не зашифрований; зберігати лише у приватній папці адміністратора, не додавати в Git і не передавати учням. Виключення з Git вже налаштовано. На Windows права приватної папки хоста перевірити окремо.

## Перевірка в окремій Ubuntu VM

Це випробування, а не перемикання учнів на інший сервер. Робочий `school-server` продовжує працювати. Нову VM запускати **без `--network`**, щоб не додати LAN-міст.

На **Mac або Windows-хості**, з кореня репозиторію:

```sh
multipass launch 24.04 --name school-recovery --cpus 2 --memory 2G --disk 12G --cloud-init lab/cloud-init.yaml
multipass transfer lab/prepare-recovery-vm.sh school-recovery:/tmp/prepare-recovery-vm.sh
multipass exec school-recovery -- sudo bash /tmp/prepare-recovery-vm.sh
multipass transfer lab/check-domain-recovery.py school-recovery:/tmp/check-domain-recovery.py
multipass transfer lab/backup-student-homes.py school-recovery:/tmp/backup-student-homes.py
```

Підготовка маскує автоматичний запуск Samba до встановлення пакетів. Відновлення використовує окремий Linux network namespace `scm-recovery`: лише loopback та dummy-інтерфейс, без зовнішнього з'єднання чи маршруту за замовчуванням. IP `192.168.1.176` існує всередині цього простору й не конфліктує з робочим сервером. Скрипт перевіряє ізоляцію перед запуском Samba, працює лише на хості з ім'ям `school-recovery` і відмовляється виконуватись за наявності звичайної бази AD.

Замінити `DOMAIN_BUNDLE_NAME` на ім'я власного збереженого архіву:

```sh
multipass transfer .local-backups/DOMAIN_BUNDLE_NAME school-recovery:/home/ubuntu/domain-bundle.tar.gz
multipass exec school-recovery -- sudo python3 /tmp/check-domain-recovery.py prepare /home/ubuntu/domain-bundle.tar.gz
multipass exec school-recovery -- sudo python3 /tmp/check-domain-recovery.py check
```

Використовувати лише власний довірений архів. `prepare` відмовляється перезаписувати наявну папку відновлення. Не створювати домен через `domain provision`: штатний `domain backup restore` відновлює його під новим ім'ям контролера `SC-RECOVERY` та зберігає SID домену й користувачів.

Скрипт `check` перевіряє:

1. Збіг версії Samba, SID домену, акаунтів учнів та Windows-комп'ютера, атрибутів H:.
2. Увесь вміст і метадані відновлених учнівських папок, узгодженість AD через `dbcheck`.
3. Запуск Samba тільки всередині ізольованої мережі, DNS SOA/SRV/A нового контролера, права SYSVOL.
4. Відповідність SID→UID/GID, Kerberos, читання та запис через SMB під обома учнями, явну відмову `NT_STATUS_ACCESS_DENIED` для чужої папки.

Для перевірки входу скрипт задає випадкові паролі student1/student2 **лише у відновленій тестовій копії**, тримає їх у пам'яті та тимчасовому файлі 0600 і прибирає файл після тесту. Паролі робочого домену й незмінного архіву на Mac це не змінює. Це перевіряє працездатність відновленої автентифікації, але не доводить вхід зі старими паролями учнів.

У випробуванні типовий шлях DNS-оновлення через TSIG дав `tsig verify failure`. Для відновленого контролера використано штатне автентифіковане RPC-оновлення `samba_dnsupdate --use-samba-tool`; `dns update command` налаштовано відповідно лише у тестовій копії. Це не дозволяє анонімні DNS-оновлення. Точну причину відмови TSIG не встановлено. Цей варіант також описано в [поясненні Samba](https://lists.samba.org/archive/samba/2019-August/225175.html).

Очікуваний результат:

```text
NATIVE_DOMAIN_RESTORE_OK
DOMAIN_SID_ACCOUNTS_FILES_DBCHECK_OK
RESTORED_DNS_SRV_A_SYSVOL_ACL_OK
student1: UID_KERBEROS_SMB_RW_PEER_DENIED_OK
student2: UID_KERBEROS_SMB_RW_PEER_DENIED_OK
DOMAIN_RECOVERY_DRILL_OK; restored Samba stopped.
```

Після тесту процес Samba зупиняється. Звіт без секретів — `/var/lib/scm-recovery/recovery-result.json`. Тестова VM містить відновлені секрети домену; вона не призначена для LAN або подальшого використання учнями. Щоб звільнити пам'ять хоста:

```sh
multipass stop school-recovery
```

Не підключати тестову VM до LAN і не запускати її як заміну робочому контролеру. Реальне аварійне відновлення потребує окремого перемикання DNS/імен, вимкнення старого контролера та перевірки Windows-клієнта.

## Фактичний результат 2026-11-25

- Комплект на Mac: `.local-backups/school-domain-20261125T195856Z-3b787f2b2ada.tar.gz`.
- SHA-256 збігся з VM: `567df25f460f57a1a245221361c970923d223af8a6f64e0cb256ca545880418f`.
- Копію передано з Mac до нової Ubuntu 24.04 ARM64 VM; штатне відновлення та всі зазначені серверні перевірки пройдено з Samba 4.19.5-Ubuntu.
- Windows-ноутбук не перемикався на відновлений контролер. Вхід Windows, його secure channel після реального перемикання та старі паролі проти відновленої копії ще не перевірені.
- Перенесення цієї ARM64-копії на AMD64 не перевірено. Для школи поки відтворюємо налаштування за інструкціями, а не вважаємо цей архів доведеним способом міграції між архітектурами.
- Розклад, ротація, шифрування архівів та зберігання на окремому фізичному носії ще не налаштовані. Архів на тому самому Mac захищає від втрати VM, але не від втрати диска Mac.
