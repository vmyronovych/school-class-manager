#!/usr/bin/env bash
# Run from the extracted, administrator-owned release.
set -euo pipefail
assets=$(cd -- "$(dirname -- "$0")" && pwd)
bundle=$(dirname "$assets")
[[ $EUID == 0 && $(hostname -s) == school-server ]]
cd "$bundle"
sha256sum --quiet --check SHA256SUMS
source /etc/os-release
[[ "$ID" == ubuntu && "$VERSION_ID" == 24.04 && -s /var/lib/samba/private/sam.ldb ]]
[[ $(cat architecture) == "$(dpkg --print-architecture)" ]]
version=$(cat VERSION)
[[ "$version" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]
realm=$(hostname -d)
[[ -n "$realm" && -d /var/lib/samba/sysvol/"$realm"/scripts ]]
exec 9>/run/scm-install.lock
flock -n 9
getent passwd scm >/dev/null || useradd --system --user-group --home-dir /var/lib/scm-panel --shell /usr/sbin/nologin scm
install -d -o scm -g scm -m 700 /var/lib/scm-panel /var/lib/scm-panel/keys
install -d -o root -g root -m 711 /srv/school /srv/school/home /var/lib/scm-enrollment
install -d -m 755 /opt/scm-panel /etc/scm-panel
target=$(mktemp -d "/opt/scm-panel/release-$version.XXXXXX")
previous=$(readlink -f /opt/scm-panel/current || true)
tar -xzf panel.tar.gz -C "$target"
cp -r "$assets" "$target/server"
chown -R root:root "$target"
chmod -R go-w "$target"
chmod 755 "$target" "$target/Scm.Api" "$target/server/scm-directory.py" "$target/server/panel-tls.sh"
sudoers=$(mktemp)
printf '%s\n' 'scm ALL=(root) NOPASSWD: /usr/local/sbin/scm-directory ""' > "$sudoers"
visudo -cf "$sudoers"
install -m 440 "$sudoers" /etc/sudoers.d/scm-panel
rm "$sudoers"
python3 "$assets/setup-panel.py"
python3 "$assets/setup-folder-redirection.py"
bash "$assets/panel-tls.sh"
netlogon=/var/lib/samba/sysvol/"$realm"/scripts
install -d -m 755 "$netlogon/scm"
openssl x509 -in /etc/scm-panel/lab-ca.crt -outform der -out "$netlogon/scm/school-ca.cer"
chmod 644 "$netlogon/scm/school-ca.cer"
msi=ScmAgent-$version-x64.msi
if [[ -e "$netlogon/scm/$msi" ]] && ! cmp -s "$msi" "$netlogon/scm/$msi"; then
  echo 'MSI version already published with different content; increment the release version.' >&2
  exit 1
fi
install -m 644 "$msi" "$netlogon/scm/.$msi.new"
mv "$netlogon/scm/.$msi.new" "$netlogon/scm/$msi"
ln -sfn "$target" /opt/scm-panel/current.new
mv -Tf /opt/scm-panel/current.new /opt/scm-panel/current
ln -sfn /opt/scm-panel/current/server/scm-directory.py /usr/local/sbin/scm-directory
install -m 755 "$assets/sync-devices.py" /usr/local/sbin/scm-sync-devices
install -m 644 "$assets"/*.service "$assets"/*.timer /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now scm-enroll.timer scm-tls.timer
systemctl start scm-enroll.service
systemctl enable scm-panel.service
if ! systemctl restart scm-panel.service || ! curl --noproxy '*' -fsS --retry 12 --retry-delay 1 --retry-connrefused --cacert /etc/scm-panel/lab-ca.crt "https://school-server.$realm:8443/healthz"; then
  if [[ -x "$previous/Scm.Api" && "$previous" != /opt/scm-panel/current ]]; then
    ln -sfn "$previous" /opt/scm-panel/current.new
    mv -Tf /opt/scm-panel/current.new /opt/scm-panel/current
    systemctl restart scm-panel.service
  fi
  exit 1
fi
echo
openssl x509 -in /etc/scm-panel/lab-ca.crt -noout -fingerprint -sha256
