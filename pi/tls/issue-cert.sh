#!/bin/bash
# issue-cert.sh <fqdn> <ip>  → /etc/scm/tls.pfx (потрібен ./ca/ca.key)
set -euo pipefail
fqdn="${1:?fqdn}"; ip="${2:?ip}"
host="${fqdn%%.*}"
openssl genrsa -out srv.key 2048
openssl req -new -key srv.key -subj "/CN=$fqdn" -out srv.csr
cat > srv.ext <<EXT
subjectAltName=DNS:$fqdn,DNS:$host,IP:$ip
extendedKeyUsage=serverAuth
EXT
openssl x509 -req -in srv.csr -CA ca/ca.crt -CAkey ca/ca.key -CAcreateserial -days 1825 -sha256 -extfile srv.ext -out srv.crt
openssl pkcs12 -export -inkey srv.key -in srv.crt -certfile ca/ca.crt -passout pass: -out tls.pfx
install -o scm -g scm -m 600 tls.pfx /etc/scm/tls.pfx
rm -f srv.key srv.csr srv.ext srv.crt tls.pfx
echo "/etc/scm/tls.pfx готово"
