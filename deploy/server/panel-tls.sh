#!/usr/bin/env bash
set -euo pipefail
umask 077
cd /etc/scm-panel
fqdn="school-server.$(hostname -d)"
[[ "$fqdn" == "$(hostname -f)" ]]
if [[ ! -f lab-ca.crt && ! -e ca.key && ! -e server.pfx ]]; then
  openssl req -x509 -newkey rsa:3072 -nodes -sha256 -days 3650 -keyout ca.key -out lab-ca.crt \
    -subj '/CN=School Class Manager CA' -addext 'basicConstraints=critical,CA:TRUE' -addext 'keyUsage=critical,keyCertSign,cRLSign'
fi
openssl x509 -in lab-ca.crt -noout -checkend 2678400 >/dev/null
if [[ -s server.pfx && -s server.crt ]] && openssl x509 -checkend 2592000 -noout -in server.crt >/dev/null; then
  exit 0
fi
tmp=$(mktemp -d .cert.XXXXXX)
trap 'rm -rf -- "$tmp"' EXIT
openssl req -newkey rsa:3072 -nodes -keyout "$tmp/key" -out "$tmp/csr" -subj "/CN=$fqdn"
printf '%s\n' "subjectAltName=DNS:$fqdn" 'extendedKeyUsage=serverAuth' 'keyUsage=critical,digitalSignature,keyEncipherment' \
  'basicConstraints=critical,CA:FALSE' > "$tmp/extensions"
openssl x509 -req -in "$tmp/csr" -CA lab-ca.crt -CAkey ca.key -CAcreateserial -out "$tmp/crt" -days 365 -sha256 -extfile "$tmp/extensions"
openssl verify -verify_hostname "$fqdn" -CAfile lab-ca.crt "$tmp/crt"
openssl pkcs12 -export -out "$tmp/pfx" -inkey "$tmp/key" -in "$tmp/crt" -certfile lab-ca.crt -passout pass:
chown root:scm "$tmp/pfx"
chmod 640 "$tmp/pfx"
mv "$tmp/pfx" server.pfx
mv "$tmp/crt" server.crt
if systemctl is-active --quiet scm-panel.service; then systemctl restart scm-panel.service; fi
