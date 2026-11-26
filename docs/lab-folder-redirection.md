# Документи та Робочий стіл учнів на сервері

## Стан

2026-11-26 на Samba DC `school-server` створено GPO **SCM - Student Documents and Desktop**, GUID `{7160EA2E-5F7D-492A-B06F-D9C1F8F21034}`. Політика прив'язана до домену; право Apply Group Policy та правила перенаправлення обмежені SID групи `scm-students`. Нові учні з панелі вже автоматично потрапляють до цієї групи. Default Domain Policy не редагувалася.

| Папка Windows | UNC | Фізичний каталог на сервері |
|---|---|---|
| Документи | `\\school-server.school.test\pupils\Documents` | `/srv/school/home/<login>/Documents` |
| Робочий стіл | `\\school-server.school.test\pupils\Desktop` | `/srv/school/home/<login>/Desktop` |

У share `pupils` вже використовується `path = /srv/school/home/%U`: однаковий UNC для різних учнів відповідає різним приватним папкам. Не додавати `%USERNAME%` до UNC — це створить зайвий вкладений каталог. Диск H: збережено; старі `student1`/`student2` мають окремі імена share, але той самий фізичний домашній каталог. Файли в корені H: залишаються на місці. Підпапки з'являться після застосування політики Windows; попередньо порожні папки всім учням не створюються.

Пройдено серверну перевірку формату GPO, її SID/ACL, SYSVOL, читання політики тимчасовим учнем через SMB, створення/читання файлів у Documents/Desktop та заборони доступу до чужої папки. Тимчасові акаунти та файли видалені. **Після виправлення заголовка політики користувач підтвердив на Windows шлях MyDocuments `\\school-server.school.test\pupils\Documents`. На сервері з’явилися Documents/Desktop; у Documents є `про мене.txt` (0 байтів). Після перезапуску й входу student2 користувач також підтвердив появу Documents/Desktop у панелі; шлях DesktopDirectory командою окремо ще не перевірено.**

## Діагностика першого застосування (2026-11-26)

Windows під `SCHOOL\vmyronovych` залишила MyDocuments у `C:\Users\vmyronovych\Documents`. Звіт `H:\folder-redirection-report.html` підтвердив членство в `scm-students`, застосовність саме нашої GPO та однакові AD/SYSVOL user revision 1. Folder Redirection завершився `The parameter is incorrect`. Журнал `H:\folder-redirection-events.txt` містив подію 511 після читання конфігурації (1004), зокрема й під час входу; одного повторення gpupdate недостатньо, щоб пояснити цей збій.

Виявлено розбіжність специфікації: текст MS-GPFR 2.2.2 називає ключ `VersionNumber`, але [приклад Microsoft 4.2](https://learn.microsoft.com/en-us/openspecs/windows_protocols/ms-gpfr/6ef51ca1-b2b2-43d7-8adf-5abfc9db5a84) та [зразок Samba](https://github.com/samba-team/samba/blob/master/source4/selftest/provisions/generalized-gpo-backup/policy/%7B1E1DC8EA-390C-4800-B327-98B56A0AEA5D%7D/User/Documents%20%26%20Settings/fdeploy1.ini.xml) використовують `version=100`. Інсталятор виправлено на `Version=100`; після цієї єдиної зміни формату Windows перейшла від помилки 511 до запиту виходу, а після повторного входу користувач підтвердив UNC для MyDocuments. Це підтверджує причину збою заголовка на цьому Windows-клієнті.

Встановлено user revision 2 (AD/GPT version 131072). Попередній файл збережено у root-only `/var/lib/scm-directory/folder-redirection/fdeploy1.ini.before-header-fix`. Міграція приймає лише точну стару керовану конфігурацію, відмовляє при сторонніх змінах і не підвищує ревізію при повторному запуску. Чотири локальні тести та серверна перевірка пройдені, тимчасові акаунти видалені. **Користувач підтвердив після повторного входу UNC-шлях Documents. Серверна перевірка підтвердила Documents/Desktop та файл `Documents/про мене.txt` (0 байтів). Останнє попередження gpupdate вимагало застосування під час входу й пропонувало вихід; воно відрізняється від попередньої помилки параметра. Перевірка DesktopDirectory та запису непорожнього файла лишається окремим кроком.**

## Застосування на Windows-клієнті

1. Увійти саме як `SCHOOL\vmyronovych` або інший учень, не як Administrator.
2. Зберегти відкриті роботи. У звичайному PowerShell виконати:

   ```powershell
   gpupdate /target:user /force
   ```

3. Якщо Windows запропонує вихід із сеансу для застосування Folder Redirection, погодитися. Інакше вийти через меню Пуск і знову ввійти тим самим учнем. Сервер і мережа мають бути доступні. Блокування екрана або перемикання користувача не замінює вихід.
4. Після входу виконати:

   ```powershell
   [Environment]::GetFolderPath('MyDocuments')
   [Environment]::GetFolderPath('DesktopDirectory')
   ```

   Очікуються два UNC з таблиці вище замість `C:\Users\...`.
5. Перевірити наявність попередніх локальних файлів. Створити окремий тестовий файл у «Документах» і на «Робочому столі» через Провідник. У вебпанелі → учень → «Файли» ці файли мають бути у `Documents`/`Desktop`.

Якщо шляхи залишилися локальними, не видаляти профіль. Зібрати `gpresult /r /scope:user` та повідомлення журналу **Applications and Services Logs → Microsoft → Windows → Folder Redirection → Operational**. `samba-tool gpo list` на сервері показує політики з правом читання, а не доводить право Apply Group Policy або успішне застосування Windows.

## Повторення на Mac або шкільному Windows-хості

Після налаштування домену, учнівських папок і панелі, з кореня цього репозиторію на хості Multipass:

```sh
multipass transfer lab/setup-folder-redirection.py lab/check-folder-redirection.py school-server:/tmp/
multipass exec school-server -- sudo python3 /tmp/setup-folder-redirection.py
multipass exec school-server -- sudo python3 /tmp/check-folder-redirection.py
```

Ubuntu-скрипти однакові для ARM64 та x64. На новій інсталяції GUID політики й SID групи відрізнятимуться; скрипт отримує їх із домену. Налаштування фіксовані для імен лабораторії `school-server`/`school.test`. Повторний запуск використовує ту саму політику й не дублює доменне посилання. Незнайома політика з таким самим ім'ям або змінений вручну `fdeploy1.ini` викликають відмову замість перезапису.

Локальні тести формату й ідемпотентності конфігурації (не потребують Samba):

```sh
python3 lab/test-folder-redirection.py
```

## Збереження даних і дисковий простір

- Використано штатний формат **MS-GPFR v1**, UTF-16 `User/Documents & Settings/fdeploy1.ini`, `Version=100`, `Flags=1001` (hex): перенаправити в повний UNC і перенести поточний вміст. Імена папок не підміняються самописним скриптом реєстру.
- ACL приватних домашніх папок уже забезпечують ізоляцію. Політика не просить Windows змінювати їх на Exclusive Access і не надає вчителям додаткових SMB-прав. Доступ учителя залишається через перевірений вебміст.
- `csc policy = disable` установлено лише на `pupils`, `student1`, `student2`. Це забороняє нове Offline Files кешування цих share; вже відкриті SMB-з'єднання можуть зберігати попередні налаштування до перепідключення. Наявний офлайн-кеш на Windows автоматично не очищався. Без мережі або сервера перенаправлені папки недоступні.
- AppData, локальні кеші, Downloads та сам профіль Windows не перенаправляються. Очищення старих профілів цим завданням не вмикається.
- Після зняття цієї політики папки залишаються на сервері (прапорець Relocate On Move вимкнено). Повернення на локальний диск — окрема міграція; видалення GPO не є командою для видалення файлів.
- Попередні `smb.conf` і доменні посилання збережені під root-only `/var/lib/scm-directory/folder-redirection/`; `policy.json` містить GUID, SID, шлях і версію встановленої політики. Існуючі старі резервні копії домену передують цьому налаштуванню; для відновлення потрібен актуальний комплект або повторне застосування скрипта.

Джерела: [Microsoft — формат MS-GPFR v1](https://learn.microsoft.com/en-us/openspecs/windows_protocols/ms-gpfr/90274772-f292-49c4-afd5-8c228b0e4a76), [прапорці перенаправлення](https://learn.microsoft.com/en-us/openspecs/windows_protocols/ms-gpfr/23526c1c-2f02-4b4e-917e-bac542beea90), [GUID розширення та папок](https://learn.microsoft.com/en-us/openspecs/windows_protocols/ms-gpfr/d3107efd-1426-4221-8db2-f243d9b241f8), [Samba — csc policy](https://www.samba.org/samba/docs/current/man-html/smb.conf.5.html#CSCPOLICY).
