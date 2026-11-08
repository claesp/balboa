"""Preview or remove generated files within the project."""

import os
from pathlib import Path
import shutil
import stat

ROOT = Path(__file__).resolve().parent.parent


def validate_target(path, root):
    path = Path(os.path.abspath(path))
    allowed = (root / "build", root / "cache")
    bytecode = (root / "__pycache__", *(root / name / "__pycache__"
                                       for name in ("balboa", "guest", "scripts", "tests")))
    if path not in bytecode and not any(path == base or base in path.parents for base in allowed):
        raise ValueError(f"Clean accepts only project build, cache, and Python cache paths: {path}")
    for component in (path, *path.parents):
        if component == root:
            break
        if component.is_symlink():
            raise ValueError(f"Clean cannot use a symbolic link as a target or parent: {component}")
    return path


def plan(args, root=ROOT):
    root = root.resolve()
    paths = [root / "__pycache__", *(root / name / "__pycache__"
                                    for name in ("balboa", "guest", "scripts", "tests"))]
    if args.build:
        paths.append(root / "build")
    if args.cache:
        paths.append(root / "cache")
    for path in args.path:
        candidate = validate_target(path, root)
        if candidate in (root / "build", root / "cache"):
            raise ValueError("Use --build or --cache to select a complete output directory.")
        paths.append(candidate)
    targets = []
    for path in sorted(set(paths), key=lambda item: (len(item.parts), str(item))):
        path = validate_target(path, root)
        if not path.exists() or any(parent in targets for parent in path.parents):
            continue
        targets.append(path)
    return targets


def allocated_bytes(path):
    total = 0
    pending = [path]
    seen = set()
    while pending:
        entry = pending.pop()
        record = entry.lstat()
        if stat.S_ISDIR(record.st_mode):
            if entry.is_mount():
                raise ValueError(f"Unmount this directory before cleanup: {entry}")
            pending.extend(entry.iterdir())
        identity = (record.st_dev, record.st_ino)
        if identity not in seen:
            total += record.st_blocks * 512
            seen.add(identity)
    return total


def busy_processes(targets, proc=Path("/proc")):
    busy = []
    for process in proc.iterdir():
        if not process.name.isdigit():
            continue
        try:
            references = [process / "cwd", *(process / "fd").iterdir()]
        except (FileNotFoundError, PermissionError):
            continue
        for reference in references:
            try:
                opened = Path(os.readlink(reference))
            except OSError:
                continue
            if any(opened == target or target in opened.parents for target in targets):
                busy.append((process.name, opened))
                break
    return busy


def clean(args, root=ROOT):
    root = root.resolve()
    targets = plan(args, root)
    sizes = [allocated_bytes(path) for path in targets]
    for path, size in zip(targets, sizes):
        print(f"{'Remove' if args.apply else 'Preview'}: {path} ({size / 1024**2:.1f} MiB allocated)")
    if not targets:
        print("No generated files match this selection.")
        return
    if not args.apply:
        print("No files were removed. Add --apply to remove this selection.")
        return
    busy = busy_processes(targets)
    if busy:
        pid, opened = busy[0]
        raise ValueError(f"Process {pid} uses {opened}. Stop it before cleanup. No files were removed.")
    for path in targets:
        validate_target(path, root)
        if path.is_dir():
            shutil.rmtree(path)
        else:
            path.unlink()
    print(f"Removed {len(targets)} generated paths ({sum(sizes) / 1024**3:.2f} GiB allocated).")
