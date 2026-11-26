#!/usr/bin/env bash
# Run as root inside the Ubuntu lab VM, on either macOS or Windows hosts.
set -euo pipefail
if [[ $EUID -ne 0 ]]; then
  echo 'Run with sudo inside the Ubuntu lab VM.' >&2
  exit 1
fi
if [[ -f /var/lib/samba/private/sam.ldb ]]; then
  echo 'An AD database already exists; this initial setup script will not change it.' >&2
  exit 1
fi
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y samba-ad-dc krb5-user bind9-dnsutils smbclient
systemctl disable --now smbd nmbd winbind
systemctl mask smbd nmbd winbind
systemctl unmask samba-ad-dc
# Provision the domain before starting samba-ad-dc.
