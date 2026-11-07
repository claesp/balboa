"""Supply a local TLS receiver for complete journal-upload tests."""

import hashlib
import json
import os
from pathlib import Path
import shutil
import socket
import ssl
import subprocess
import time

ROOT = Path(__file__).resolve().parent.parent
IMAGE = "localhost/balboa-log-collector:10"


def lab_logger(args):
    from .cli import run, source_lock

    directory = args.directory.resolve()
    name = "balboa-logs-" + hashlib.sha256(str(directory).encode()).hexdigest()[:12]
    existing = subprocess.run(["podman", "container", "inspect", name], capture_output=True, text=True)
    if existing.returncode == 0:
        state = json.loads(existing.stdout)[0]
        if state["Config"]["Labels"].get("balboa.lab_directory") != str(directory):
            raise ValueError("The existing container does not belong to this lab directory.")
        if args.stop:
            run(["podman", "stop", name])
            run(["podman", "rm", name])
            return
        if not state["State"]["Running"]:
            run(["podman", "start", name])
        print(directory / "client")
        return
    if args.stop:
        print("The lab collector is not running.")
        return
    if not 1024 <= args.port <= 65535:
        raise ValueError("The lab collector port must be from 1024 to 65535.")
    directory.mkdir(parents=True, exist_ok=True)
    directory.chmod(0o700)
    if not (directory / "ca.pem").exists():
        if list(directory.iterdir()):
            raise ValueError("The new lab directory must be empty.")
        run(["openssl", "req", "-x509", "-newkey", "rsa:3072", "-nodes", "-sha256", "-days", "2",
             "-addext", "basicConstraints=critical,CA:TRUE", "-addext", "keyUsage=critical,keyCertSign,cRLSign",
             "-subj", "/CN=Balboa Lab CA", "-keyout", directory / "ca.key", "-out", directory / "ca.pem"], capture_output=True)
        for role in ("server", "client"):
            target = directory / role
            target.mkdir(mode=0o700)
            run(["openssl", "req", "-new", "-newkey", "rsa:3072", "-nodes", "-sha256", "-subj", f"/CN=balboa-lab-{role}",
                 "-keyout", target / f"{role}.key", "-out", target / f"{role}.csr"], capture_output=True)
            extension = target / "extensions"
            extension.write_text("basicConstraints=CA:FALSE\nkeyUsage=digitalSignature,keyEncipherment\nextendedKeyUsage=" +
                                 ("serverAuth\nsubjectAltName=IP:10.0.2.2,IP:127.0.0.1\n" if role == "server" else "clientAuth\n"))
            run(["openssl", "x509", "-req", "-in", target / f"{role}.csr", "-CA", directory / "ca.pem",
                 "-CAkey", directory / "ca.key", "-CAcreateserial", "-days", "2", "-sha256", "-extfile", extension,
                 "-out", target / f"{role}.pem"], capture_output=True)
            shutil.copyfile(directory / "ca.pem", target / "ca.pem")
    run(["openssl", "x509", "-in", directory / "ca.pem", "-checkend", "300", "-noout"], capture_output=True)
    bundle = directory / "server/bundle.pem"
    bundle.write_text((directory / "server/server.pem").read_text() + (directory / "server/server.key").read_text())
    bundle.chmod(0o600)
    logs = directory / "logs"
    logs.mkdir(exist_ok=True, mode=0o700)
    run(["podman", "build", "--build-arg", f'BASE={source_lock()["container"]}', "-f",
         ROOT / "containers/log-collector.Containerfile", "-t", IMAGE, ROOT])
    command = ["podman", "run", "-d", "--name", name, "--label", f"balboa.lab_directory={directory}",
               "--read-only", "--tmpfs", "/run", "--cap-drop=all", "--security-opt=no-new-privileges",
               "--user", str(os.getuid()), "-p", f"127.0.0.1:{args.port}:19532",
               "-v", f"{directory / 'server'}:/tls:ro", "-v", f"{logs}:/logs:rw"]
    if os.getuid() != 0:
        command += ["--userns=keep-id"]
    run(command + [IMAGE])
    context = ssl.create_default_context(cafile=str(directory / "ca.pem"))
    context.load_cert_chain(directory / "client/client.pem", directory / "client/client.key")
    deadline = time.monotonic() + 15
    while True:
        try:
            with socket.create_connection(("127.0.0.1", args.port), timeout=1) as connection:
                with context.wrap_socket(connection, server_hostname="10.0.2.2"):
                    break
        except (OSError, ssl.SSLError) as error:
            if time.monotonic() >= deadline:
                raise ValueError(f"The test collector did not accept TLS: {error}. Read podman logs {name}.")
            time.sleep(0.2)
    print(f"The lab receiver is https://10.0.2.2:{args.port}.")
    print(directory / "client")
