# Скрипти домашньої лабораторії

Актуальний стан: [checkpoint](../docs/checkpoint-2026-11-26.md). Порядок встановлення: [VM](../docs/lab.md) → [Samba](../docs/lab-samba.md) → [папки](../docs/lab-files.md) → [панель](../docs/lab-panel.md) → [перенаправлення](../docs/lab-folder-redirection.md).

| Файли | Де виконувати / призначення |
| --- | --- |
| `cloud-init.yaml`, `netplan.home.yaml` | Конфігурація нової Ubuntu VM та домашньої LAN; адаптувати мережу перед школою |
| `install-samba.sh`, `provision-samba.py`, `set-admin-password.py` | Ubuntu school-server; встановлення, одноразове створення домену, інтерактивний пароль |
| `setup-student-homes.py` | Ubuntu school-server; приватні папки початкових student1/student2 |
| `install-panel.sh`, `setup-panel.py`, `scm-panel.service`, `scm-directory.py` | Встановлення панелі та root bridge; точні команди й передумови в lab-panel.md |
| `setup-folder-redirection.py` | Ubuntu school-server; керована GPO, її відома міграція й налаштування SMB-кешування |
| `panel-smoke.py`, `check-folder-redirection.py` | Живі перевірки проти Samba; створюють і прибирають тимчасові акаунти/файли |
| `check-panel-admin.py` | Перевірка нормалізації Administrator та SID без зміни його пароля |
| `backup-student-homes.py`, `backup-domain.py` | Ручні лабораторні копії; перед читанням/запуском ознайомитися з відповідними docs/lab-*.md |
| `prepare-recovery-vm.sh`, `check-domain-recovery.py` | Лише ізольована school-recovery; не підключати відновлений DC до робочої LAN |
| `test-folder-redirection.py`, `validate.py` | Локальні перевірки/CI; не змінюють VM, акаунти чи мережу |

`validate.py` перевіряє синтаксис Python/Bash та тести генерації GPO. Це не перевірка застосування політики Windows. Не виконувати всі скрипти підряд: provisioning, backup і recovery мають різні передумови.
