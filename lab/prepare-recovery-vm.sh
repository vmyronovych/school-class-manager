#!/usr/bin/env bash
# Only for the disposable recovery VM; never run on the working DC.
set -euo pipefail
if [[ $EUID -ne 0 || $(hostname) != school-recovery ]]; then
  echo 'Run as root only inside school-recovery.' >&2
  exit 1
fi
if [[ -e /var/lib/samba/private/sam.ldb ]]; then
  echo 'An existing domain was found; refusing to change it.' >&2
  exit 1
fi
systemctl mask samba-ad-dc smbd nmbd winbind
apt-get update -qq
DEBIAN_FRONTEND=noninteractive apt-get install -y -qq \
  samba-ad-dc krb5-user smbclient bind9-dnsutils libnss-winbind
