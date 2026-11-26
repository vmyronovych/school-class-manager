#!/usr/bin/env python3
"""Configure two private home shares in the SCHOOL.TEST lab; run as root on its DC."""

import os
from pathlib import Path
import pwd
import re
import secrets
import shutil
import socket
import stat
import subprocess
import tempfile
import time

from samba import ldb
from samba.auth import system_session
from samba.param import LoadParm
from samba.samdb import SamDB

USERS = ("student1", "student2")
ROOT = Path("/srv/school/home")
CONFIG = Path("/etc/samba/smb.conf")
BEGIN = "# BEGIN SCM LAB STUDENT HOMES"
END = "# END SCM LAB STUDENT HOMES"


def directory(path, uid, gid, mode):
    if path.is_symlink():
        raise RuntimeError(f"Refusing symlink: {path}")
    if path.exists():
        info = path.stat()
        if not stat.S_ISDIR(info.st_mode) or info.st_uid != uid:
            raise RuntimeError(f"Unexpected directory owner/type: {path}")
    else:
        path.mkdir(mode=mode)
        os.chown(path, uid, gid)
    # Only the directory itself; never change existing children's ownership or ACLs.
    path.chmod(mode)


def main():
    if os.geteuid() != 0 or socket.gethostname() != "school-server":
        raise SystemExit("Run with sudo inside the school-server lab VM.")
    lp = LoadParm()
    lp.load_default()
    if lp.get("realm") != "SCHOOL.TEST" or lp.get("workgroup") != "SCHOOL":
        raise SystemExit("This script is only for the SCHOOL.TEST lab.")
    original = CONFIG.read_text()
    if BEGIN in original or END in original:
        if original.count(BEGIN) != 1 or original.count(END) != 1:
            raise RuntimeError("Invalid managed block markers.")
        base, block = original.split(BEGIN)
        _, tail = block.split(END)
        if tail.strip():
            raise RuntimeError("Managed block must be the last section.")
    else:
        base = original
    for name in USERS:
        if re.search(r"^\s*\[" + name + r"\]\s*$", base, re.M | re.I):
            raise RuntimeError(f"Unmanaged share already exists: {name}")

    db = SamDB(url="/var/lib/samba/private/sam.ldb", session_info=system_session(), lp=lp)
    accounts = {}
    for name in USERS:
        result = db.search(expression=f"(sAMAccountName={name})", attrs=["homeDrive", "homeDirectory"])
        if not result:
            if name == "student1":
                raise RuntimeError("Create and test student1 first, following docs/lab-samba.md.")
            # No password is logged, persisted in a script, or passed in process arguments.
            db.newuser(name, "Aa1!" + secrets.token_urlsafe(36), description="School lab second pupil")
            result = db.search(expression=f"(sAMAccountName={name})", attrs=["homeDrive", "homeDirectory"])
            print(f"Created {name}; set its password privately before Windows login.")
        if len(result) != 1:
            raise RuntimeError(f"Expected exactly one user: {name}")
        expected = {"homeDrive": "H:", "homeDirectory": rf"\\school-server.school.test\{name}"}
        for key, value in expected.items():
            if key in result[0] and str(result[0][key][0]) != value:
                raise RuntimeError(f"Existing {key} for {name} differs; review before changing.")
        accounts[name] = (result[0].dn, expected)

    directory(Path("/srv/school"), 0, 0, 0o711)
    directory(ROOT, 0, 0, 0o711)
    for name in USERS:
        for attempt in range(10):
            try:
                account = pwd.getpwnam("SCHOOL\\" + name)
                break
            except KeyError:
                if attempt == 9:
                    raise RuntimeError(f"No Unix identity for {name}; check winbind/NSS.")
                time.sleep(1)
        directory(ROOT / name, account.pw_uid, account.pw_gid, 0o700)

    shares = [BEGIN]
    for name in USERS:
        shares.append(f"""
[{name}]
    csc policy = disable
    path = {ROOT / name}
    valid users = "SCHOOL\\{name}"
    read only = no
    browseable = no
    guest ok = no
    create mask = 0600
    directory mask = 0700
    force create mode = 0600
    force directory mode = 0700
    acl_xattr:ignore system acls = no
""")
    candidate = base.rstrip() + "\n\n" + "\n".join(shares) + END + "\n"
    with tempfile.NamedTemporaryFile(mode="w", dir=CONFIG.parent, delete=False) as file:
        temporary = Path(file.name)
        file.write(candidate)
    try:
        subprocess.run(["testparm", "-s", str(temporary)], check=True, capture_output=True)
        if candidate != original:
            backup = CONFIG.with_name("smb.conf.before-student-homes")
            if not backup.exists():
                shutil.copy2(CONFIG, backup)
            temporary.chmod(0o644)
            os.replace(temporary, CONFIG)
        subprocess.run(["smbcontrol", "all", "reload-config"], check=True)
    finally:
        temporary.unlink(missing_ok=True)

    for name, (dn, values) in accounts.items():
        message = ldb.Message()
        message.dn = dn
        for key, value in values.items():
            message[key] = ldb.MessageElement(value, ldb.FLAG_MOD_REPLACE, key)
        db.modify(message)
        print(f"{name}: H: -> {values['homeDirectory']}")
    print("SERVER_HOMES_CONFIGURED; verify Windows logon and cross-user access next.")


if __name__ == "__main__":
    main()
