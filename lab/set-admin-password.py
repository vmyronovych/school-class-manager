#!/usr/bin/env python3
"""Privately set the lab Administrator password and verify the same value with Kerberos."""

import getpass
import os
import socket
import subprocess
import sys
import tempfile
import warnings

from samba.auth import system_session
from samba.param import LoadParm
from samba.samdb import SamDB
from samba import ldb


def set_and_verify(account, password):
    lp = LoadParm()
    lp.load_default()
    if lp.get("realm") != "SCHOOL.TEST":
        raise RuntimeError("This helper is only for the SCHOOL.TEST lab.")
    db = SamDB(url="/var/lib/samba/private/sam.ldb", session_info=system_session(), lp=lp)
    db.setpassword("(sAMAccountName=" + ldb.binary_encode(account) + ")", password)
    with tempfile.TemporaryDirectory(prefix="scm-password-check-") as directory:
        env = dict(os.environ, KRB5CCNAME="FILE:" + directory + "/ticket")
        env.pop("KRB5_TRACE", None)
        check = subprocess.run(
            ["kinit", account + "@SCHOOL.TEST"], input=password + "\n",
            text=True, encoding="utf-8", capture_output=True, env=env, timeout=20,
        )
        if check.returncode:
            return False
        return subprocess.run(["klist", "-s"], env=env, capture_output=True).returncode == 0


def main():
    if os.geteuid() != 0 or socket.gethostname() != "school-server":
        raise SystemExit("Run with sudo inside the school-server lab VM.")
    if not sys.stdin.isatty():
        raise SystemExit("Run in your own interactive terminal; passwords must remain hidden.")
    warnings.simplefilter("error", getpass.GetPassWarning)
    password = getpass.getpass("New Administrator password: ")
    confirm = getpass.getpass("Repeat password: ")
    if not password or password != confirm or any(c in password for c in "\r\n\0"):
        raise SystemExit("Inputs do not match or are invalid. Nothing changed.")
    del confirm
    try:
        success = set_and_verify("Administrator", password)
    except ldb.LdbError:
        raise SystemExit("Samba rejected the password. Choose a new password meeting its complexity and history policy.")
    except subprocess.TimeoutExpired:
        raise SystemExit("Password changed, but Kerberos verification timed out. Report this result.")
    finally:
        del password
    if not success:
        raise SystemExit("PASSWORD_CHANGED_BUT_KERBEROS_FAILED")
    print("PASSWORD_SET_AND_KERBEROS_OK")


if __name__ == "__main__":
    main()
