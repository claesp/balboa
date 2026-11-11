"""Copy the installation media files to the corresponding paths on the target."""

import hashlib
import json
from pathlib import Path
import stat
import subprocess
import sys


def payload_files(root):
    if not stat.S_ISDIR(root.lstat().st_mode):
        raise ValueError("balboa-files must be a directory.")
    pending = [root]
    files = []
    while pending:
        for path in pending.pop().iterdir():
            relative = path.relative_to(root)
            mode = path.lstat().st_mode
            if relative.parts[0] in {"dev", "proc", "run", "sys"}:
                raise ValueError(f"The payload cannot install to /{relative}.")
            if stat.S_ISDIR(mode):
                pending.append(path)
            elif stat.S_ISREG(mode) and not stat.S_IMODE(mode) & 0o7000:
                files.append((relative, stat.S_IMODE(mode)))
            else:
                raise ValueError(f"Use a regular file or directory without special file permissions: {relative}")
    return sorted(files)


def payload_digest(root):
    records = []
    for path, mode in payload_files(root):
        with (root / path).open("rb") as source:
            records.append((path.as_posix(), mode, hashlib.file_digest(source, "sha256").hexdigest()))
    return hashlib.sha256(json.dumps(records).encode()).hexdigest()


def install_tree(source, target):
    changed = []
    for relative, mode in payload_files(source):
        directory = target
        for part in relative.parts[:-1]:
            directory /= part
            try:
                existing = directory.lstat()
            except FileNotFoundError:
                directory.mkdir(mode=0o755)
                directory.chmod(0o755)
                changed.append("/" + directory.relative_to(target).as_posix())
            else:
                if not stat.S_ISDIR(existing.st_mode):
                    raise ValueError(f"The installation path is not a directory: {directory}")
        destination = target / relative
        if destination.is_symlink() or (destination.exists() and not destination.is_file()):
            raise ValueError(f"The installation path is not a regular file: {destination}")
        subprocess.run(["install", "-m", f"{mode:04o}", "--", source / relative, destination], check=True)
        changed.append("/" + relative.as_posix())
    return changed


if __name__ == "__main__":
    source, target = map(Path, sys.argv[1:])
    paths = install_tree(source, target)
    for offset in range(0, len(paths), 128):
        subprocess.run(["chroot", target, "/usr/sbin/restorecon", "-F", "--", *paths[offset:offset + 128]], check=True)
