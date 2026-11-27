"""Exercise the published executable and the Windows service on the disposable CI host."""
import http.server
import json
import os
from pathlib import Path
import queue
import secrets
import ssl
import subprocess
import sys
import tempfile
import threading
import winreg


def run(*args, **kwargs):
    return subprocess.run(args, check=True, timeout=90, **kwargs)


def check_status(report):
    with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows NT\CurrentVersion") as version:
        build, _ = winreg.QueryValueEx(version, "CurrentBuildNumber")
    assert report["computerName"].upper() == os.environ["COMPUTERNAME"].upper()
    assert report["windowsBuild"] == build
    assert report["systemDriveFreeGiB"] >= 0
    assert report["nonSystemProfileCount"] >= 0


def install_msi(msi, action, directory):
    result = subprocess.run(["msiexec.exe", action, msi, "/qn", "/norestart", "/l*v", directory / "msi.log"], timeout=120)
    if result.returncode not in (0, 3010):
        lines = (directory / "msi.log").read_text(encoding="utf-16", errors="replace").splitlines()
        raise RuntimeError(f"MSI {action}: {result.returncode} " + "\n".join(line for line in lines if "Error " in line))


def test_agent(msi, directory):
    import shutil
    install_msi(msi, "/i", directory)
    agent_directory = Path(os.environ["ProgramFiles"]) / "School Class Manager" / "Agent"
    installed, = agent_directory.glob("[0-9]*/Scm.Agent.exe")
    exe = directory / "Scm.Agent.exe"
    shutil.copyfile(installed, exe)
    run("powershell", "-NoProfile", "-Command", "if ((Get-Service ScmAgent).Status -ne 'Running') { throw 'Service stopped' }")
    install_msi(msi, "/x", directory)
    assert not installed.exists()
    check_status(json.loads(subprocess.check_output([exe, "status"], timeout=60)))
    key = secrets.token_hex(24).upper()
    reports = queue.Queue()

    class Receiver(http.server.BaseHTTPRequestHandler):
        def do_POST(self):
            if self.path != "/agent/status" or self.headers.get("Authorization") != "Bearer " + key:
                self.send_error(403)
                return
            body = self.rfile.read(int(self.headers["Content-Length"])) if "Content-Length" in self.headers else self.read_chunks()
            reports.put(json.loads(body))
            self.send_response(204)
            self.end_headers()

        def read_chunks(self):
            body = bytearray()
            while size := int(self.rfile.readline().strip(), 16):
                body.extend(self.rfile.read(size))
                self.rfile.read(2)
            self.rfile.readline()
            return body

    def openssl(*args):
        run("openssl", *args, cwd=directory)

    openssl("req", "-x509", "-newkey", "rsa:2048", "-nodes", "-days", "1", "-subj", "/CN=Test CA",
            "-addext", "basicConstraints=critical,CA:TRUE", "-keyout", "ca.key", "-out", "ca.pem")
    openssl("req", "-new", "-newkey", "rsa:2048", "-nodes", "-subj", "/CN=localhost",
            "-keyout", "server.key", "-out", "server.csr")
    (directory / "extensions").write_text("subjectAltName=DNS:localhost\nextendedKeyUsage=serverAuth\n")
    openssl("x509", "-req", "-in", "server.csr", "-CA", "ca.pem", "-CAkey", "ca.key", "-CAcreateserial",
            "-days", "1", "-extfile", "extensions", "-out", "server.pem")
    openssl("x509", "-in", "ca.pem", "-outform", "der", "-out", "ca.cer")
    with http.server.ThreadingHTTPServer(("127.0.0.1", 0), Receiver) as server:
        tls = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        tls.load_cert_chain(directory / "server.pem", directory / "server.key")
        server.socket = tls.wrap_socket(server.socket, server_side=True)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            run(exe, "install", f"https://localhost:{server.server_port}", directory / "ca.cer", input=key + "\n", text=True)
            check_status(reports.get(timeout=60))
            install_msi(msi, "/i", directory)
            service_config = subprocess.check_output(["sc.exe", "qc", "ScmAgent"], text=True)
            assert str(installed).lower() in service_config.lower()
            check_status(reports.get(timeout=60))
            run("powershell", "-NoProfile", "-Command", "Restart-Service ScmAgent -ErrorAction Stop")
            check_status(reports.get(timeout=60))
        finally:
            server.shutdown()
            install_msi(msi, "/x", directory)
            assert not installed.exists()


if __name__ == "__main__":
    with tempfile.TemporaryDirectory() as temp:
        test_agent(Path(sys.argv[1]).resolve(), Path(temp))
