#!/usr/bin/env bash
set -euo pipefail
umask 077
export DEBIAN_FRONTEND=noninteractive
test "$(id -u)" = 0
# Never source JSON as shell or accept secret shell arguments.
install -d -m 700 /etc/classroom
install -m 600 /tmp/classroom-config.json /etc/classroom/config.json
install -d -m 755 /usr/local/lib/classroom
for script in /tmp/classroom-scripts/*.sh /tmp/classroom-scripts/*.py; do
  install -m 755 "$script" /usr/local/lib/classroom/
done
chmod 755 /usr/local/lib/classroom/*.sh /usr/local/lib/classroom/*.py
apt-get update
apt-get install -y samba samba-ad-dc samba-dsdb-modules samba-vfs-modules winbind krb5-user smbclient ldb-tools dnsutils acl attr chrony python3-samba gnupg
systemctl disable --now smbd nmbd winbind || true
systemctl stop samba-ad-dc || true
systemctl disable samba-ad-dc || true
python3 /usr/local/lib/classroom/setup.py
install -d /etc/systemd/system/samba-ad-dc.service.d
cat > /etc/systemd/system/samba-ad-dc.service.d/storage.conf <<'EOF'
[Unit]
RequiresMountsFor=/srv/classroom /var/lib/samba
ConditionPathExists=/srv/classroom/domain-ready
EOF
systemctl daemon-reload
dpkg-query -W > /srv/classroom/packages.lock
if test -f /srv/classroom/domain-ready; then
  test -f /srv/classroom/domain/private/sam.ldb
  testparm -s >/dev/null
  systemctl unmask samba-ad-dc
  systemctl enable --now samba-ad-dc
else
  echo 'Empty server prepared. No domain created. Run domain.py create interactively after approval.'
fi
