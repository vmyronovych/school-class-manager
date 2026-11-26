#!/usr/bin/env bash
# Input: a trusted release tar and this repository's lab files in /tmp/scm-panel-install.
set -euo pipefail
if [[ $EUID -ne 0 || $(hostname) != school-server ]]; then
  echo 'Run as root inside school-server.' >&2; exit 1
fi
release=${1:?Path to release tar required}
assets=/tmp/scm-panel-install
getent passwd scm >/dev/null || useradd --system --home-dir /var/lib/scm-panel --shell /usr/sbin/nologin scm
install -d -m 700 /var/lib/scm-panel
install -d -o scm -g scm -m 700 /var/lib/scm-panel/keys
chown scm:scm /var/lib/scm-panel
install -d -m 755 /opt/scm-panel /etc/scm-panel
stamp=$(date -u +%Y%m%dT%H%M%SZ)
target=/opt/scm-panel/release-$stamp
mkdir -m 755 "$target"
tar -xzf "$release" -C "$target"
chown -R root:root "$target"
chmod -R go-w "$target"
chmod 755 "$target/Scm.Api"
install -o root -g root -m 755 "$assets/scm-directory.py" /usr/local/sbin/scm-directory
printf '%s\n' 'scm ALL=(root) NOPASSWD: /usr/local/sbin/scm-directory ""' > /etc/sudoers.d/scm-panel
chmod 440 /etc/sudoers.d/scm-panel
visudo -cf /etc/sudoers.d/scm-panel
python3 "$assets/setup-panel.py"
if [[ ! -e /etc/scm-panel/server.pfx ]]; then
  # Private lab CA. Keys never leave the server or enter the release archive.
  openssl req -x509 -newkey rsa:3072 -nodes -sha256 -days 3650 \
    -keyout /etc/scm-panel/ca.key -out /etc/scm-panel/lab-ca.crt \
    -subj '/CN=School Lab CA' -addext 'basicConstraints=critical,CA:TRUE' \
    -addext 'keyUsage=critical,keyCertSign,cRLSign' 2>/dev/null
  openssl req -newkey rsa:2048 -nodes -sha256 -keyout /etc/scm-panel/server.key \
    -out /etc/scm-panel/server.csr -subj '/CN=school-server.school.test' 2>/dev/null
  printf '%s\n' 'subjectAltName=DNS:school-server.school.test,IP:192.168.1.176' \
    'extendedKeyUsage=serverAuth' 'keyUsage=critical,digitalSignature,keyEncipherment' \
    'basicConstraints=critical,CA:FALSE' > /etc/scm-panel/server.ext
  openssl x509 -req -in /etc/scm-panel/server.csr -CA /etc/scm-panel/lab-ca.crt \
    -CAkey /etc/scm-panel/ca.key -CAcreateserial -out /etc/scm-panel/server.crt \
    -days 365 -sha256 -extfile /etc/scm-panel/server.ext 2>/dev/null
  openssl pkcs12 -export -out /etc/scm-panel/server.pfx -inkey /etc/scm-panel/server.key \
    -in /etc/scm-panel/server.crt -certfile /etc/scm-panel/lab-ca.crt -passout pass:
fi
chmod 600 /etc/scm-panel/ca.key /etc/scm-panel/server.key
chown root:scm /etc/scm-panel/server.pfx
chmod 640 /etc/scm-panel/server.pfx
chmod 644 /etc/scm-panel/lab-ca.crt
cp /etc/scm-panel/lab-ca.crt "$target/wwwroot/lab-ca.crt"
openssl x509 -in /etc/scm-panel/lab-ca.crt -outform der \
  -out /var/lib/samba/sysvol/school.test/scripts/school-lab-ca.cer
chmod 644 /var/lib/samba/sysvol/school.test/scripts/school-lab-ca.cer
ln -sfn "$target" /opt/scm-panel/current
install -m 644 "$assets/scm-panel.service" /etc/systemd/system/scm-panel.service
systemctl daemon-reload
systemctl enable scm-panel.service
systemctl restart scm-panel.service
python3 - <<'PY'
import ssl
import time
import urllib.error
import urllib.request
context = ssl.create_default_context(cafile='/etc/scm-panel/lab-ca.crt')
for attempt in range(20):
    try:
        with urllib.request.urlopen('https://192.168.1.176:8443/healthz', context=context, timeout=2) as response:
            if response.status == 200:
                break
    except (urllib.error.URLError, TimeoutError):
        pass
    time.sleep(1)
else:
    raise SystemExit('Panel did not become healthy; inspect journalctl -u scm-panel.')
PY
printf '%s\n' 'Panel: https://192.168.1.176:8443'
openssl x509 -in /etc/scm-panel/lab-ca.crt -noout -fingerprint -sha256
