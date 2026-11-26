# Лабораторія: Ubuntu VM та доступ із Windows

Мета першого кроку: запустити Ubuntu та перевірити доступ до її SSH-порту з окремого Windows-ноутбука. Наступний етап описано в [тестовому домені Samba](lab-samba.md).

Удома сервер працює у Multipass на MacBook M1 (16 GB), клієнт — Windows 10 Pro Education. У школі сервер має працювати в Ubuntu VM на Windows-ноутбуці. Команди нижче виконуються на **хості сервера**, крім явно позначеної перевірки на **учнівському Windows-клієнті**.

## 1. Підготовка хоста

### Mac — виконано

Встановлено Multipass 1.17.2 офіційним інсталятором Canonical. Пакет завантажено через `brew fetch --cask multipass`; перевірено контрольну суму Homebrew, підпис Canonical і нотаризацію Apple. Встановлення виконано системним `installer` з правами адміністратора; це не встановлення через `brew install`.

Для повторення достатньо завантажити macOS `.pkg` з [офіційної сторінки](https://canonical.com/multipass/install), відкрити інсталятор і пройти встановлення. Потім у Terminal:

```sh
multipass version
multipass list
multipass get local.driver
multipass networks
```

До створення VM перевірено: клієнт і служба `1.17.2+mac`, драйвер `qemu`, список VM порожній. Активний інтерфейс Mac — `en0` (Wi-Fi), IP Mac — `192.168.1.229`, шлюз — `192.168.1.1`. Це домашні параметри на 2026-11-25, їх не переносимо у школу.

### Шкільний Windows — ще не перевірено

1. Перевірити редакцію Windows, процесор, RAM, вільний диск і підтримку віртуалізації. Домашній клієнт із Pro Education — інший пристрій; характеристики шкільного хоста поки невідомі.
2. Підключити серверний ноутбук до мережі кабелем Ethernet. За документацією Multipass, Wi-Fi інтерфейси не показуються в `multipass networks` на Windows.
3. Виконати передумови з [офіційної інструкції встановлення](https://canonical.com/multipass/docs/stable/how-to-guides/install-multipass/), зокрема увімкнути Virtual Machine Platform, якщо її ще не ввімкнено. Якщо Windows потребує перезапуску, завершити його перед створенням VM.
4. Установити Multipass офіційним Windows `.msi`. Відкрити нове вікно PowerShell і виконати ті самі чотири команди перевірки, що вище. Записати версію, драйвер і доступні мережі.
5. Вибрати мережу, що дає VM доступ до фізичної LAN. Якщо Ethernet/відповідного віртуального комутатора немає в списку, спочатку налаштувати мережу відповідно до драйвера й перевірити її. Не вважати приватний NAT достатнім для учнівських ПК у LAN.

## 2. Створення VM

Параметри лабораторії: Ubuntu 24.04 LTS, 2 CPU, 4 GB RAM, диск 30 GB. Це розмір тестового середовища для двох учнів; місткість сервера школи визначимо окремо. Перед запуском перевірити `multipass list`: якщо `school-server` уже існує, спочатку оглянути її через `multipass info school-server`.

Відкрити термінал у корені копії цього репозиторію. Для обох платформ використовується [lab/cloud-init.yaml](../lab/cloud-init.yaml): він явно встановлює `Europe/Kyiv`. Це усуває виявлену на Mac помилку першого запуску: успадкований `Europe/Kiev` відсутній у цьому образі Ubuntu. Файл не містить паролів або домашніх мережевих адрес.

На **Mac**, для фактично виявленого інтерфейсу `en0`:

```sh
multipass launch 24.04 --name school-server --cpus 2 --memory 4G --disk 30G --network en0 --cloud-init lab/cloud-init.yaml
```

На **шкільному Windows-хості**, у PowerShell, підставити точну назву перевіреної LAN-мережі з `multipass networks` замість тексту в кутових дужках:

```powershell
$LabNetwork = '<назва LAN-мережі з multipass networks>'
multipass launch 24.04 --name school-server --cpus 2 --memory 4G --disk 30G --network "$LabNetwork" --cloud-init lab/cloud-init.yaml
```

Очікуваний результат — `Launched: school-server`. Multipass завантажує образ відповідно до архітектури хоста: ARM64 на M1, AMD64 на Intel/AMD. На шкільному хості створюємо нову VM та повторюємо налаштування; диск ARM64 VM не переносимо як завантажуваний диск на Intel/AMD.

`--network` додає LAN-інтерфейс до службового інтерфейсу Multipass. Для підключення учнівського ПК використовувати **LAN IP**, а не приватну адресу Multipass. Першу адресу видає DHCP; перед налаштуванням домену закріпити адресу, як описано в розділі 5.

## 3. Перевірки з хоста сервера

Команди однакові в Terminal на Mac та PowerShell на Windows:

```sh
multipass list
multipass info school-server
multipass exec school-server -- cat /etc/os-release
multipass exec school-server -- uname -m
multipass exec school-server -- ip -br address show scope global
multipass exec school-server -- systemctl is-active ssh
multipass exec school-server -- cloud-init status --wait
multipass exec school-server -- timedatectl show --property=Timezone --value
```

Очікується: VM у стані `Running`, Ubuntu 24.04, архітектура `aarch64` на M1 або `x86_64` на Intel/AMD, LAN-адреса у мережі клієнта, SSH `active`, cloud-init `done` без помилок, часовий пояс `Europe/Kyiv`. Вхід у сервер із хоста: `multipass shell school-server`.

## 4. Перевірка з учнівського Windows-ноутбука

Підключити Windows-клієнт до тієї самої домашньої мережі. У **PowerShell на клієнті** підставити фактичний LAN IP VM:

```powershell
Test-NetConnection -ComputerName <LAN-IP-VM> -Port 22
```

Критерій успіху: `TcpTestSucceeded : True`. Це підтверджує доступність SSH-порту з іншого ПК, але ще не підтверджує автентифікацію SSH, роботу Samba або доменний вхід. Поки не змінювати DNS Windows і не приєднувати його до домену.

Для домашньої VM станом на 2026-11-25 команда така:

```powershell
Test-NetConnection -ComputerName 192.168.1.176 -Port 22
```

## 5. Закріплення LAN IP у роутері

На хості сервера визначити MAC саме LAN-інтерфейсу Ubuntu VM:

```sh
multipass exec school-server -- ip -br link
multipass exec school-server -- ip -br address
```

Для поточної домашньої VM LAN-інтерфейс — `eth1`, MAC — `52:54:00:03:93:d5`, IP — `192.168.1.176`. Додатково перевірено через `multipass exec school-server -- networkctl status eth1`: DHCP4 Client ID збігається з цим MAC.

У правилі резервування DHCP роутера потрібно зіставити MAC LAN-інтерфейсу VM з вибраним IP. У школі знову визначити MAC та IP відповідної VM; MAC домашньої VM й інтерфейс `eth1` не переносити автоматично. Якщо VM створити заново без фіксованого MAC, правило теж потрібно перевірити.

Користувач виправив початковий запис із MAC MacBook на `52:54:00:03:93:d5` → `192.168.1.176`; підтверджено другим скриншотом від 2026-11-25. Проте після перезапуску VM отримала через DHCP `192.168.1.177`. Причину на боці роутера/мосту не встановлено; саме резервування не забезпечило очікуваної адреси у цій перевірці.

Тому додано статичну адресу всередині Ubuntu. Резервування в роутері залишаємо для цієї VM. Використовується [lab/netplan.home.yaml](../lab/netplan.home.yaml), який змінює лише `eth1`; службовий `eth0` лишається на DHCP.

Команди з кореня репозиторію на хості (Terminal або PowerShell):

```sh
multipass transfer lab/netplan.home.yaml school-server:/tmp/school-lan.yaml
multipass exec school-server -- sudo install -m 0600 /tmp/school-lan.yaml /etc/netplan/60-school-lan.yaml
multipass exec school-server -- sudo netplan generate
multipass exec school-server -- sudo netplan apply
multipass restart school-server
multipass exec school-server -- ip -4 -br address
```

Для школи спочатку створити окрему копію YAML зі шкільними значеннями: ідентифікатор LAN-інтерфейсу з `sudo netplan get`, IP/префікс, шлюз та DNS. Адреса має бути зарезервована для VM або виключена з DHCP-пулу, без конфлікту з іншими пристроями. Не застосовувати домашній файл без адаптації. Після `netplan generate` не повинно бути помилок; після перезапуску очікується задана статична адреса та успішний `Test-NetConnection` з клієнта. У лабораторії доступ для керування зберігається через окремий `eth0`; відкат LAN-файлу: `multipass exec school-server -- sudo rm /etc/netplan/60-school-lan.yaml`, потім `multipass exec school-server -- sudo netplan apply` (повернення до DHCP).

## 6. Щоденна робота

Виконувати на хості сервера:

```sh
multipass stop school-server
multipass start school-server
multipass info school-server
```

Після старту перевірити актуальний LAN IP. Сервер у VM доступний, поки працює хост і його мережа; для шкільного використання окремо перевіримо сон, автозапуск і відновлення після перезапуску Windows.

## Фактичний стан перевірки

- 2026-11-25: установлення Multipass і визначення мережі на Mac — пройдено.
- Створення `school-server` командою з `--cloud-init lab/cloud-init.yaml` — пройдено: `Running`, Ubuntu 24.04.5 LTS, `aarch64`, 2 CPU, 4 GB RAM, диск 30 GB; образ `50e24e1fb79e` (образ `24.04` у каталозі Multipass мав версію `20261017`).
- `cloud-init status --wait` — `status: done`, код завершення 0; розширений статус не містить помилок. Часовий пояс — `Europe/Kyiv`, SSH — `active`.
- LAN IP — статична `192.168.1.176/24` на `eth1`; службовий IP Multipass — DHCP `192.168.252.3` на `eth0`. Статичну адресу та доступність SSH перевірено після перезапуску.
- Доступ із Mac до LAN IP: `nc -vz -G 5 192.168.1.176 22` — успішно.
- Початкова порожня VM без спільного cloud-init мала помилку `Europe/Kiev`; її видалено й створено заново з явним `Europe/Kyiv`. Даних користувача в ній не було.
- Доступ із домашнього Windows-клієнта — пройдено, підтверджено скриншотом користувача від 2026-11-25: `Test-NetConnection -ComputerName 192.168.1.176 -Port 22`, `SourceAddress: 192.168.1.174`, `InterfaceAlias: Wi-Fi`, `TcpTestSucceeded: True`. Перший етап (VM та мережевий доступ із клієнта) завершено.
- Резервування IP у роутері виправлене на MAC `52:54:00:03:93:d5` (скриншот користувача), але перевірка DHCP після перезапуску дала `192.168.1.177`. Додатково застосована статична конфігурація Netplan; тепер `192.168.1.176` зберігається після перезапуску (див. розділ 5).
- Samba та її DNS працюють, перевірені з Mac і після перезапуску; деталі — [lab-samba.md](lab-samba.md). Доменний вхід Windows, резервне копіювання та розгортання на Windows-хості — ще не перевірено.

Довідка: [мережі Multipass](https://canonical.com/multipass/docs/latest/how-to-guides/manage-instances/set-up-custom-networking/), [відмінності платформ](https://canonical.com/multipass/docs/latest/explanation/platform/). Підтримка драйверів залежить від версії; фіксувати фактичний вивід команд на цільовому хості.
