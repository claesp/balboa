# Clean generated files

The `clean` command selects generated files within this repository.
Its default selection contains only Python bytecode caches.
A bytecode cache contains compiled Python files that Python recreates when needed.
The default command shows paths and allocated disk space without removal.

1. Stop the QEMU machines and log collectors that use the files.
2. Retain the required assessment reports and release manifests.
3. Operate the cleanup commands from the repository root on the Linux build host.

## Preview and removal

Preview the default selection with the following command.

```sh
python3 -m balboa clean
```

To remove the selected files, add `--apply`.

```sh
python3 -m balboa clean --apply
```

The `make clean` command removes the same Python caches.
These default commands retain images, virtual disks, reports, and the official media cache.

## Selected outputs

1. Use `--path` to select a file or directory under the project `build/` or `cache/` directory.
2. To select more than one item, repeat `--path`.
3. Use the exact path from the preview for removal.

```sh
python3 -m balboa clean --path build/old-laptop
python3 -m balboa clean --path build/old-laptop --apply
```

To replace a disposable VM, select its complete work directory.
The command removes the disk, firmware variables, and retained VM logs.
The next installation can then create a new work directory at that path.

```sh
python3 -m balboa clean --path build/qemu-old-laptop
python3 -m balboa clean --path build/qemu-old-laptop --apply
```

## Complete removal

Use `--build` to select the complete `build/` directory.
Before you add `--apply`, save the files you need.
With both flags, the command removes all installation ISOs, virtual disks, generated credentials, previews, and reports in `build/`.

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
Host permissions control which processes the command can see.
Before removal, stop the services that use the selected files.

## Repository review

The November 8 cleanup retained the project source, required photo, font, and license files.
It removed obsolete intermediate builds, old test ISOs, and disposable disks from completed test sessions.
It retained the recorded reports, screenshots, and image previews at their documented paths.

That cleanup retained the `build/laptop-dvd/` render, laptop DVD ISO, and `build/qemu-laptop/` VM.
It also retained the official media cache and the private site input.
The retained reports describe historical test results and do not require the removed disposable disks.
GiB means 1,073,741,824 bytes.
The cleanup recovered 33.94 GiB of allocated space.

The local record resides under `build/cleanup-20261108/`.
It contains the exact selected paths, removal log, preservation results, and 54 passing local tests.
The laptop VM remained available throughout the cleanup.
