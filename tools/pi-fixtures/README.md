# pi-fixtures

Реальні виводи команд з Pi для тестів парсерів у `Scm.Infrastructure.Tests`. Ім'я: `<команда>.<samba-версія>.txt`, напр. `smbstatus-b.4.19.7.txt`, `scm-status.4.19.7.json`, `samba-tool-user-show.4.19.7.txt`, `ls-snapshots.txt`, `df-B1.txt`.

Зняти після M0:

```
ssh admin@dc1 'sudo smbstatus -b'            > smbstatus-b.$V.txt
ssh admin@dc1 'sudo scm-status'              > scm-status.$V.json
ssh admin@dc1 'sudo samba-tool user show 4a.test' > samba-tool-user-show.$V.txt
ssh admin@dc1 'ls -1 /srv/data/home/.snapshots'    > ls-snapshots.txt
ssh admin@dc1 'df -B1 --output=used,size /srv/data' > df-B1.txt
ssh admin@dc1 'sudo samba-tool --version'
```

Замінити реальні прізвища на тестові перед комітом. Нова команда в коді = нова фікстура в тому ж коміті.
