# pi-fixtures

Реальні виводи команд з Pi для тестів парсерів у `Scm.Infrastructure.Tests`. Ім'я: `<команда>.<samba-версія>.<txt|json|ldif>`, напр. `smbstatus-b.4.19.7.txt`, `scm-status.4.19.7.json`, `students.4.19.7.ldif`; для команд, що не залежать від Samba, — без версії: `ls-snapshots.txt`, `df-B1.txt`.

Зняти після M0:

```
ssh admin@dc1 'sudo smbstatus -b'            > smbstatus-b.$V.txt
ssh admin@dc1 'sudo scm-status'              > scm-status.$V.json
ssh admin@dc1 'sudo samba-tool user show test.uchen.2015' > samba-tool-user-show.$V.txt
ssh admin@dc1 'ls -1 /srv/data/home/.snapshots'    > ls-snapshots.txt
ssh admin@dc1 'df -B1 --output=used,size /srv/data' > df-B1.txt
ssh admin@dc1 'sudo samba-tool --version'
# LDIF для LdapDirectory (сесія 3 M1); серед тестових учнів мають бути заблокований, вимкнений і такий, що не входив
ssh admin@dc1 "sudo ldbsearch -H /var/lib/samba/private/sam.ldb -b 'OU=Uchni,DC=ad,DC=school,DC=lan' '(objectClass=user)' sAMAccountName sn givenName memberOf userAccountControl lockoutTime lastLogonTimestamp pwdLastSet profilePath" > students.$V.ldif
ssh admin@dc1 "sudo ldbsearch -H /var/lib/samba/private/sam.ldb -b 'DC=ad,DC=school,DC=lan' '(&(objectClass=group)(cn=uchni-*))' cn member" > classes.$V.ldif
```

Замінити реальні прізвища на тестові перед комітом. Нова команда в коді = нова фікстура в тому ж коміті.
