#!/bin/bash
# Idempotent-встановлення School Class Manager на Pi. Запускати під sudo після Етапу 4 docs/deployment.md.
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)

id scm >/dev/null 2>&1 || useradd -r -s /usr/sbin/nologin -d /var/lib/scm scm
install -d -o scm -g scm -m 750 /opt/scm /var/lib/scm /var/lib/scm/keys /etc/scm

install -o root -g root -m 755 "$here"/sbin/scm-user "$here"/sbin/scm-status "$here"/sbin/scm-logs \
  "$here"/sbin/scm-update "$here"/sbin/snap.sh "$here"/sbin/backup.sh "$here"/sbin/add-uchni.sh /usr/local/sbin/
install -o root -g root -m 440 "$here"/sudoers.d/scm /etc/sudoers.d/scm
visudo -c >/dev/null

install -d /etc/nftables.d
install -m 644 "$here"/nftables/scm.nft /etc/nftables.d/scm.nft
grep -q 'nftables.d' /etc/nftables.conf || echo 'include "/etc/nftables.d/*.nft"' >> /etc/nftables.conf
systemctl enable --now nftables && systemctl reload nftables

install -m 644 "$here"/scm.service "$here"/scm-update.service /etc/systemd/system/
systemctl daemon-reload

if [ ! -f /etc/scm/tls.pfx ]; then
  echo ">> TLS: запустіть pi/tls/make-ca.sh (один раз) і pi/tls/issue-cert.sh dc1.ad.school.lan 192.168.1.2"
fi
if [ ! -f /etc/scm/appsettings.Production.json ]; then
  cat > /etc/scm/appsettings.Production.json <<JSON
{
  "Domain": { "Realm": "ad.school.lan", "BaseDn": "DC=ad,DC=school,DC=lan", "StudentsOu": "OU=Uchni",
              "TeacherGroup": "vchyteli", "AdminGroup": "Domain Admins", "LdapUrl": "ldapi:///" },
  "Paths": { "Home": "/srv/data/home", "Class": "/srv/data/class", "Snapshots": ".snapshots", "Db": "/var/lib/scm/scm.db" },
  "Tls": { "PfxPath": "/etc/scm/tls.pfx", "PfxPassword": "" },
  "PasswordPolicy": { "Syllables": 2, "AppendDigit": true }
}
JSON
  chown scm:scm /etc/scm/appsettings.Production.json; chmod 640 /etc/scm/appsettings.Production.json
  echo ">> Перевірте /etc/scm/appsettings.Production.json"
fi

if [ ! -e /opt/scm/current ]; then
  echo ">> Немає релізу: запустіть scm-update (потрібен доступ до github.com) або розпакуйте tar.gz у /opt/scm/<версія> і зробіть символьне посилання current"
else
  systemctl enable --now scm
fi
echo "install.sh done"
