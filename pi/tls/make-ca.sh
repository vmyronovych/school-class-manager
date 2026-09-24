#!/bin/bash
# Створює кореневий CA «SCHOOL Class CA» у ./ca (ключ — офлайн, у конверт). Запускати один раз.
set -euo pipefail
mkdir -p ca && cd ca
[ -f ca.key ] && { echo "ca.key already exists"; exit 1; }
openssl genrsa -out ca.key 4096
openssl req -x509 -new -key ca.key -sha256 -days 3650 -subj "/CN=SCHOOL Class CA/O=School" -out ca.crt
echo "ca.crt → імпортувати у GPO Trusted Root; ca.key — у конверт, не на Pi"
