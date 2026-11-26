#!/usr/bin/env python3
"""Create school.test once, inside a fresh school-server Ubuntu lab VM."""

import argparse
import ipaddress
import json
import os
from pathlib import Path
import re
import shutil
import socket
import subprocess


def run(*args):
    return subprocess.run(args, check=True, text=True, capture_output=True).stdout


def configure_hosts(address):
    mapping = f"{address} school-server.school.test school-server"
    hosts = Path("/etc/hosts")
    lines = [line for line in hosts.read_text().splitlines()
             if "school-server" not in line.split("#", 1)[0].split()[1:]]
    hosts.write_text("\n".join(lines) + "\n" + mapping + "\n")
    Path("/etc/cloud/cloud.cfg.d/99-school-hosts.cfg").write_text("manage_etc_hosts: false\n")
    # Multipass vendor-data can retain manage_etc_hosts=true. Keep its template
    # correct too, so the next boot cannot map the DC back to 127.0.1.1.
    template = Path("/etc/cloud/templates/hosts.debian.tmpl")
    backup = Path(str(template) + ".before-school-lab")
    if not backup.exists():
        shutil.copyfile(template, backup)
    lines = [line for line in template.read_text().splitlines()
             if not line.strip().startswith("127.0.1.1")
             and "school-server" not in line.split("#", 1)[0].split()[1:]]
    template.write_text("\n".join(lines) + "\n" + mapping + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--address", required=True, type=ipaddress.IPv4Address)
    parser.add_argument("--lan-interface", required=True)
    parser.add_argument("--dns-forwarder", required=True, type=ipaddress.IPv4Address)
    args = parser.parse_args()
    if os.geteuid() != 0 or socket.gethostname() != "school-server":
        parser.error("Run as root inside the school-server lab VM.")
    if not re.fullmatch(r"[a-zA-Z0-9_.-]+", args.lan_interface):
        parser.error("Invalid interface name.")
    if args.address == args.dns_forwarder or args.dns_forwarder.is_loopback:
        parser.error("DNS forwarder must be an upstream DNS server.")
    if Path("/var/lib/samba/private/sam.ldb").exists():
        parser.error("An AD database exists. Do not provision again or delete it.")
    address = str(args.address)
    interfaces = json.loads(run("ip", "-j", "-4", "address", "show", "dev", args.lan_interface))
    if not any(a["local"] == address for i in interfaces for a in i["addr_info"]):
        parser.error("The requested address is not assigned to the LAN interface.")

    # Preserve originals, and refuse to overwrite evidence of an earlier attempt.
    originals = [Path(p) for p in ("/etc/hosts", "/etc/krb5.conf", "/etc/samba/smb.conf", "/etc/resolv.conf")]
    for path in originals:
        if Path(str(path) + ".before-school-lab").exists():
            parser.error("An earlier setup attempt exists; inspect it before continuing.")
    for path in originals:
        shutil.copyfile(path, str(path) + ".before-school-lab")

    fqdn = "school-server.school.test"
    configure_hosts(address)
    Path("/etc/samba/smb.conf").unlink()

    # Samba chooses a random Administrator password. Capture its output in memory
    # so that the password never enters a terminal transcript or a log file.
    result = subprocess.run([
        "samba-tool", "domain", "provision", "--realm=SCHOOL.TEST", "--domain=SCHOOL",
        "--server-role=dc", "--dns-backend=SAMBA_INTERNAL", "--use-rfc2307",
        "--host-name=school-server", f"--host-ip={address}",
        f"--option=interfaces=lo {args.lan_interface}", "--option=bind interfaces only=yes",
        f"--option=dns forwarder={args.dns_forwarder}",
    ], text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    if result.returncode:
        # Provisioning errors are useful; password-bearing lines are never emitted.
        print("\n".join(line for line in result.stdout.splitlines()
                        if "password" not in line.lower()))
        raise SystemExit("Provisioning failed. Inspect partial state; do not rerun blindly.")
    del result

    shutil.copyfile("/var/lib/samba/private/krb5.conf", "/etc/krb5.conf")
    run("testparm", "--suppress-prompt")
    run("systemctl", "disable", "--now", "systemd-resolved")
    resolver = Path("/etc/resolv.conf")
    resolver.unlink()
    resolver.write_text("nameserver 127.0.0.1\nsearch school.test\n")
    run("systemctl", "enable", "--now", "samba-ad-dc")
    print("Created SCHOOL.TEST (SCHOOL), controller: " + fqdn)
    print("Set your own Administrator password locally: sudo samba-tool user setpassword Administrator")


if __name__ == "__main__":
    main()
