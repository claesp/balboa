# Clean generated files

The `clean` command selects generated files within this repository.
Its default selection contains only Python bytecode caches.
A bytecode cache contains compiled Python files that Python recreates when needed.
The default command shows paths and allocated disk space without removal.

Operate these commands from the repository root on the Linux build host.
Stop the relevant QEMU machines and log collectors before cleanup.
Retain required assessment reports and release manifests before removal.

## Preview and removal

Preview the default selection:

```sh
python3 -m balboa clean
```

Add `--apply` to remove the selected files:

```sh
python3 -m balboa clean --apply
```

The `make clean` command performs this same Python cache removal.
These default commands retain images, virtual disks, reports, and the official media cache.

## Selected outputs

Use `--path` to select a file or directory under the project `build/` or `cache/` directory.
Repeat `--path` to select more than one item.
Use the exact path from the preview for removal.

```sh
python3 -m balboa clean --path build/old-laptop
python3 -m balboa clean --path build/old-laptop --apply
```

To replace a disposable VM, select its complete work directory.
This removes the disk, firmware variables, and retained VM logs together.
The next installation can then create a new work directory at that path.

```sh
python3 -m balboa clean --path build/qemu-old-laptop
python3 -m balboa clean --path build/qemu-old-laptop --apply
```

## Complete removal

Use `--build` to select the complete `build/` directory.
With `--apply`, this removes all installation ISOs, virtual disks, generated credentials, previews, and reports in that directory.

```sh
python3 -m balboa clean --build
python3 -m balboa clean --build --apply
```

Use `--cache` to select the official media cache and its signature files.
The next fetch requires another authenticated download.
The flags also work together.

```sh
python3 -m balboa clean --build --cache
python3 -m balboa clean --build --cache --apply
```

The command does not remove Podman images or unrelated host files.
A symbolic link is a path that refers to another path.
The command rejects source paths, targets with symbolic link parents, and mounted directories.
It removes nested symbolic links without following their destinations.
It refuses removal when a visible host process uses a selected file or directory.
Process visibility depends on host permissions, so stop the relevant services before removal.

## Repository review

The November 8 cleanup retains the project source, required photo, font, and license files.
It removes obsolete intermediate builds, old test ISO files, and disposable disks from completed test sessions.
It retains the recorded reports, screenshots, and current image previews at their documented paths.

The recent `build/laptop-dvd/` render, laptop DVD ISO, and `build/qemu-laptop/` VM remain available.
The cleanup retains the official media cache and the private site input.
The retained reports describe historical test results and do not require the removed disposable disks.
GiB means 1,073,741,824 bytes.
The cleanup recovers 33.94 GiB of allocated space.

The local record resides under `build/cleanup-20261108/`.
It contains the exact selected paths, removal log, preservation results, and 54 passing local tests.
The active laptop VM remains available throughout the cleanup.
