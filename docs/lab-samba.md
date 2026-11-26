# Лабораторія: тестовий домен Samba

Передумова — [Ubuntu VM з перевіреною мережею та стабільною LAN-адресою](lab.md). Цей крок створює новий тестовий домен `school.test` у свіжій VM `school-server`. Він не переносить існуючий домен і не є процедурою відновлення.

Команди хоста виконуються з кореня репозиторію в Terminal на Mac або PowerShell на Windows. Скрипти виконуються **всередині Ubuntu**, тому однакові для обох хостів. На Windows-хості процедура ще не перевірена.

## Параметри домашньої лабораторії

| Параметр | Значення |
| --- | --- |
| DNS-домен / Kerberos realm | `school.test` / `SCHOOL.TEST` |
| Коротка назва домену | `SCHOOL` |
| Контролер домену | `school-server.school.test` |
| LAN IP та інтерфейс | `192.168.1.176`, `eth1` |
| DNS forwarder (для зовнішніх імен) | Домашній роутер `192.168.1.1` |

`school.test` — назва лабораторії. У школі можна повторити цю лабораторію на новій VM, підставивши її IP, інтерфейс та DNS forwarder. До створення домену з реальними учнівськими обліковими записами окремо визначити постійне доменне ім'я, зберігання даних, час Windows-клієнтів, резервне копіювання та перевірене відновлення. Ці скрипти обмежені тестовим `school.test`.

## 1. Установлення пакетів

На хості:

```sh
multipass transfer lab/install-samba.sh school-server:/tmp/install-samba.sh
multipass exec school-server -- sudo bash /tmp/install-samba.sh
```

Скрипт встановлює `samba-ad-dc`, `krb5-user`, `bind9-dnsutils`, `smbclient`; вимикає окремі служби `smbd`, `nmbd`, `winbind`, оскільки ними керуватиме процес контролера домену. При наявності бази AD скрипт припиняє роботу.

## 2. Одноразове створення домену

На хості, для **домашніх** мережевих параметрів:

```sh
multipass transfer lab/provision-samba.py school-server:/tmp/provision-samba.py
multipass exec school-server -- sudo python3 /tmp/provision-samba.py --address 192.168.1.176 --lan-interface eth1 --dns-forwarder 192.168.1.1
```

На шкільному Windows-хості змінити три мережеві аргументи на перевірені значення шкільної VM. Перед запуском IP має бути закріплений, а DNS forwarder — доступний із VM. Шкільний роутер і DNS усієї мережі ця команда не змінює.

Скрипт перевіряє наявність адреси на вказаному інтерфейсі, відмовляється повторно створювати існуючий домен, зберігає оригінали конфігурації з суфіксом `.before-school-lab`. Він задає FQDN у `/etc/hosts` та шаблоні cloud-init для збереження після перезапуску; налаштовує Samba на `lo` та LAN-інтерфейсі, щоб службова адреса Multipass не реєструвалася як адреса контролера.

Для DNS Ubuntu використовує локальну Samba (`127.0.0.1`), яка передає запити зовнішніх імен роутеру. `systemd-resolved` у VM вимкнений; встановлено згенеровану Samba конфігурацію Kerberos та автозапуск `samba-ad-dc`.

Samba створює випадковий пароль Administrator. Скрипт перехоплює її вивід у пам'ять і не друкує та не зберігає цей пароль. Наступним кроком користувач задає власний пароль через локальний доступ `sudo`.

## 3. Особисто задати пароль адміністратора

У власному терміналі на **хості сервера**:

```sh
multipass shell school-server
```

Після входу **в Ubuntu**:

```sh
sudo samba-tool user setpassword Administrator
```

Увести обраний пароль двічі в прихованих запитах. Пароль не додавати аргументом команди, не записувати в репозиторій і не надсилати в чат. Зберегти його у своєму менеджері паролів. Очікується повідомлення про успішне встановлення пароля.

Тут же можна перевірити Kerberos (пароль знову вводиться приховано):

```sh
kinit Administrator@SCHOOL.TEST
klist
kdestroy
```

Очікується квиток `krbtgt/SCHOOL.TEST@SCHOOL.TEST`. `kdestroy` видаляє квиток після перевірки. Вийти з Ubuntu командою `exit`.

## 4. Перевірки сервера

На хості:

```sh
multipass exec school-server -- systemctl is-active samba-ad-dc
multipass exec school-server -- hostname -f
multipass exec school-server -- dig @127.0.0.1 school-server.school.test A +short
multipass exec school-server -- dig @127.0.0.1 _ldap._tcp.dc._msdcs.school.test SRV +short
multipass exec school-server -- dig @127.0.0.1 _kerberos._tcp.school.test SRV +short
multipass exec school-server -- sudo samba-tool dbcheck --cross-ncs
```

Очікується `active`, FQDN `school-server.school.test`, лише LAN IPv4 сервера в A-записі, SRV записи контролера на портах 389 і 88, база без помилок. Після перезапуску VM ці результати мають зберегтися. Перевірка `dbcheck` без `--fix` нічого не виправляє.

З **учнівського Windows-клієнта**, без зміни його DNS:

```powershell
Resolve-DnsName school-server.school.test -Server 192.168.1.176 -Type A
Resolve-DnsName _ldap._tcp.dc._msdcs.school.test -Server 192.168.1.176 -Type SRV
Test-NetConnection 192.168.1.176 -Port 445
```

Це перевірка доступу до доменних служб. Наступний крок — налаштування DNS та приєднання клієнта, описані нижче.

## 5. DNS учнівського Windows-клієнта

Виконувати у **Windows PowerShell від імені адміністратора на учнівському ноутбуці**. Підтверджена назва його поточного інтерфейсу — `Wi-Fi`. На іншому ПК спочатку визначити потрібний інтерфейс через `Get-NetIPConfiguration`.

Перед змінами один раз зберегти початкову конфігурацію (файл знадобиться для повернення початкових налаштувань):

```powershell
netsh interface ipv4 show config name="Wi-Fi" | Out-File -Encoding utf8 "$env:USERPROFILE\school-lab-network-before.txt"
```

Установити адресу Samba як DNS для цього інтерфейсу й перевірити пошук домену вже **без** явного параметра `-Server`:

```powershell
Set-DnsClientServerAddress -InterfaceAlias "Wi-Fi" -ServerAddresses 192.168.1.176
Clear-DnsClientCache
Resolve-DnsName _ldap._tcp.dc._msdcs.school.test -Type SRV
Get-CimInstance Win32_ComputerSystem | Select-Object Name, PartOfDomain, Domain
```

Очікується контролер `school-server.school.test`, порт `389`; для ще не приєднаного домашнього ПК — `PartOfDomain: False`. Якщо ПК уже належить іншому домену, не переходити до приєднання: спочатку уточнити його призначення та доступ локального адміністратора. Якщо пошук домену не проходить, не виконувати `Add-Computer`, а перевірити фактичні DNS-адреси інтерфейсів.

Поки DNS клієнта вказує на VM, для розв'язання імен потрібні запущена VM і доступ до Mac. Для повернення до домашньої мережі звіритися зі збереженою конфігурацією: якщо DNS раніше отримувався через DHCP, виконати `Set-DnsClientServerAddress -InterfaceAlias "Wi-Fi" -ResetServerAddresses`; якщо він був статичним — відновити початкові адреси через `-ServerAddresses`. Після цього `Clear-DnsClientCache`. Скидання DNS саме по собі не виводить комп'ютер із домену.

## 6. Приєднання Windows до тестового домену

Цей крок виконувати після успішної перевірки попереднього розділу. Потрібен доступ до локального облікового запису адміністратора ноутбука, щоб можна було ввійти локально й після експерименту. У тому самому адміністративному Windows PowerShell:

```powershell
Add-Computer -DomainName "school.test" -Credential (Get-Credential "SCHOOL\Administrator") -PassThru -Verbose -ErrorAction Stop
```

У системному запиті ввести особисто встановлений пароль Administrator. Очікується `HasSucceeded: True`. Команда не містить `-Restart` і не перезавантажує Windows автоматично. Після успішного результату зберегти відкриті документи й перезавантажити ноутбук вручну. При помилці не повторювати приєднання навмання.

Після перезапуску ввійти у звичний **локальний** обліковий запис (за потреби у полі логіну — `.\ім'я_локального_користувача`) і перевірити в адміністративному PowerShell:

```powershell
Get-CimInstance Win32_ComputerSystem | Select-Object Name, PartOfDomain, Domain
Test-ComputerSecureChannel -Verbose
```

Очікується `PartOfDomain: True`, домен `school.test` та результат перевірки каналу `True`. Для першого доменного входу створимо окремого тестового учня наступним кроком; Administrator використовується тут для приєднання ПК.

Команди перевірено за документацією Microsoft: [налаштування DNS](https://learn.microsoft.com/en-us/powershell/module/dnsclient/set-dnsclientserveraddress), [Add-Computer](https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.management/add-computer?view=powershell-5.1). Виконання на домашньому Windows-клієнті підтверджено користувачем; результати наведено нижче.

## 7. Перший тестовий учень

Після підтвердження `PartOfDomain: True`, `school.test` та `Test-ComputerSecureChannel: True` створити звичайний доменний акаунт `student1`. Це технічний тестовий логін без даних реального учня; правила логінів для школи визначатимемо окремо.

На **хості сервера** (Mac Terminal або Windows PowerShell):

```sh
multipass shell school-server
```

У **Ubuntu**, особисто користувачем:

```sh
sudo samba-tool user create student1
```

Пароль вводиться двічі приховано; вибрати окремий від Administrator пароль, що відповідає чинній політиці домену. Не додавати пароль у команду або репозиторій. Очікується `User 'student1' added successfully`. Якщо користувач уже існує, не видаляти його й не повторювати створення: перевірити стан. Стандартне створення не додає учня до Domain Admins або локальних адміністраторів Windows.

На **Windows-клієнті** зберегти роботу, вибрати «Змінити користувача», потім «Інший користувач», увести `SCHOOL\student1` і щойно встановлений пароль. Дочекатися створення першого локального профілю Windows. У звичайному PowerShell під учнем виконати:

```powershell
whoami
```

Очікується `school\student1`. Це перевіряє перший інтерактивний доменний вхід учня. Продовження з приватними папками двох учнів та диском H: — [lab-files.md](lab-files.md).

## Якщо приєднання відхиляє облікові дані

Зафіксована помилка Windows: `The user name or password is incorrect` при `Add-Computer` з `SCHOOL\Administrator`. Вона ще не встановлює першопричину. Не перезапускати Windows і не змінювати пароль або політики навмання; скасувати поточний запит облікових даних і перевірити вхід безпосередньо на сервері.

У власному Terminal на Mac:

```sh
multipass shell school-server
```

У Ubuntu, під звичайним користувачем `ubuntu`:

```sh
kinit Administrator@SCHOOL.TEST
```

Ввести той самий пароль приховано. У разі успіху `kinit` зазвичай нічого не друкує; виконати `klist` і перевірити наявність `krbtgt/SCHOOL.TEST@SCHOOL.TEST`, після чого `kdestroy`. У разі помилки передати лише текст помилки. Цей крок відділяє перевірку облікових даних на сервері від Windows domain join; він сам по собі ще не перевіряє приєднання.

Автоматичне відтворення точного Windows-сценарію недоступне: агент не керує цим ноутбуком і не має приватного пароля. Свідчення відмови — скриншот користувача; наступний контрольний результат — виконаний користувачем `kinit`. Діагностичні зміни політик і скидання пароля поки не виконувалися.

### Установлення й перевірка тим самим введеним паролем

Користувач показав `Changed password OK`, а потім дві відмови `kinit: Password incorrect`. На тимчасовому акаунті перевірено: неправильний пароль відхиляється, правильний дає квиток, після `samba-tool user setpassword` новий пароль теж дає квиток. Трасування підтвердило KDC `192.168.1.176:88`. Це перевіряє загальну працездатність Kerberos, але ще не встановлює причину відмови саме для Administrator.

Щоб виключити відмінність між значенням під час установлення та повторним введенням у `kinit`, додано [lab/set-admin-password.py](../lab/set-admin-password.py). На хості (Mac або Windows) встановити його всередині VM:

```sh
multipass transfer lab/set-admin-password.py school-server:/tmp/set-admin-password.py
multipass exec school-server -- sudo install -m 0755 /tmp/set-admin-password.py /usr/local/sbin/scm-set-admin-password
```

У поточній домашній VM це вже виконано. У **власному інтерактивному терміналі Ubuntu** користувач запускає:

```sh
sudo scm-set-admin-password
```

Команда задає **новий** пароль Administrator: запитує його двічі приховано, передає Samba та `kinit` те саме значення з пам'яті, без аргументів командного рядка й без запису пароля у файли або вивід. Тимчасовий Kerberos-квиток видаляється після перевірки. Успіх — `PASSWORD_SET_AND_KERBEROS_OK`; лише після цього повторити приєднання Windows з новим паролем. Якщо виведено `PASSWORD_CHANGED_BUT_KERBEROS_FAILED`, пароль уже змінено, але причина відмови потребує подальшої діагностики.

Помічник перевірено на тимчасовому акаунті; Administrator агентом не змінювався. Усі тимчасові акаунти, квитки та діагностичний скрипт після перевірок видалено. Користувач підтвердив скриншотом `PASSWORD_SET_AND_KERBEROS_OK`: новий пароль Administrator прийнято й Kerberos-квиток отримано. Повторне приєднання Windows із новим паролем завершилося `HasSucceeded: True`; після перезапуску користувач підтвердив членство в домені й працездатність захищеного каналу.

## Фактичні результати

- Встановлено Samba `4.19.5-Ubuntu` (пакет `2:4.19.5+dfsg-4ubuntu9.8`) на Ubuntu 24.04.5 ARM64.
- `samba-ad-dc` — `active`; DNS A та SRV записи LDAP/Kerberos правильні, зовнішні DNS-імена розв'язуються.
- З Mac перевірено DNS через `192.168.1.176`, TCP 88, 389, 445 — доступні.
- Перевірено 3840 об'єктів AD, 0 помилок.
- Повторний виклик скрипта створення домену відхилено до змін: `An AD database exists`, код завершення 2. Скрипт не перезаписує існуючу AD.
- Після перезапуску з остаточним виправленням шаблону cloud-init: FQDN `school-server.school.test`, LAN IP `192.168.1.176`, Samba `active`, правильні A/SRV записи, TCP 445 доступний із Mac; час Ubuntu синхронізовано, cloud-init завершився без помилок.
- Користувач підтвердив установлення власного пароля Administrator у терміналі. Пароль не передавався в чат і не зберігався в репозиторії.
- Скриншот користувача від 2026-11-25 підтвердив із Windows `192.168.1.174` (Wi-Fi): SRV `_ldap._tcp.dc._msdcs.school.test` через DNS `192.168.1.176` повертає `school-server.school.test:389`; TCP 445 — `TcpTestSucceeded: True`.
- Наступний скриншот від 2026-11-25 підтвердив успішний SRV-пошук без `-Server`: `school-server.school.test:389`. Перед приєднанням Windows мав `PartOfDomain: False`, `Domain: WORKGROUP`. Передумови для приєднання перевірено.
- Kerberos-вхід Administrator із новим паролем підтверджено скриншотом `PASSWORD_SET_AND_KERBEROS_OK`.
- Скриншот користувача підтвердив успішне `Add-Computer`: `HasSucceeded: True`, комп’ютер `DESKTOP-N8KR882`; Windows повідомив про необхідність перезапуску. На сервері `samba-tool computer list` також показав `DESKTOP-N8KR882$`.
- Скриншот після перезапуску Windows підтвердив: `DESKTOP-N8KR882`, `PartOfDomain: True`, `Domain: school.test`; `Test-ComputerSecureChannel -Verbose` повернув `True` та повідомлення, що канал у доброму стані.
- Користувач створив `student1`, дочекався першого налаштування профілю Windows і підтвердив `whoami` → `school\student1`. Перший інтерактивний доменний вхід учня пройдено.
- Перевірка Samba підтвердила активний звичайний акаунт `student1` (`userAccountControl=512`), основну групу Domain Users (`primaryGroupID=513`), відсутність додаткових прямих членств у групах і заповнені `lastLogon` / `lastLogonTimestamp`.
- Створено student2, налаштовано дві приватні папки та атрибути H:. Серверні перевірки Unix-ізоляції пройдено. Користувач підтвердив H: і збереження файла під student1, запит інших облікових даних при відкритті папки student2, а потім успішний вхід під student2, створення власного файла та відсутність доступу до файлів student1. Деталі — [lab-files.md](lab-files.md). Ручне копіювання учнівських папок на Mac та ізольоване відновлення перевірено; див. [lab-backup.md](lab-backup.md). Ця файлова копія не охоплює домен; окремий комплект домену й успішний ізольований тест відновлення описані в [lab-domain-recovery.md](lab-domain-recovery.md).

Основа процедури: [Ubuntu Server — Samba AD/DC](https://ubuntu.com/server/docs/how-to/samba/provision-samba-ad-controller/). Скрипт додатково враховує два мережеві інтерфейси Multipass і приховує випадково згенерований початковий пароль.

Діагностика невдалого приєднання (2026-11-25): Administrator має `userAccountControl=512`, `badPwdCount=0`, значення блокування відсутнє; сервер синхронізований за часом. Під час початкової діагностики `samba-tool computer list` показував лише `SCHOOL-SERVER$`. Користувач підтвердив дві відмови `kinit` для Administrator. На тимчасових акаунтах створення, скидання пароля й Kerberos працюють; KDC правильний. Після особистого запуску `sudo scm-set-admin-password` користувач отримав `PASSWORD_SET_AND_KERBEROS_OK`. Серверна перевірка Administrator тепер успішна; точну причину попередньої відмови не доведено. Повторення тієї самої команди `Add-Computer` із новим паролем завершилося успішно; комп’ютер з’явився в AD. Членство й захищений канал після перезапуску підтверджені; `student1` уже успішно ввійшов у Windows. Особисті папки двох учнів і взаємну ізоляцію перевірено користувачем із Windows; ручне резервне копіювання папок і перевірку відновлення також виконано, див. [lab-backup.md](lab-backup.md).
