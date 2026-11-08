# Fixed storage

Production installations use a fixed 128 GB disk budget by default.
GB means 1,000,000,000 bytes in this project.
Lab installations use a fixed 32 GB disk by default.

LVM divides one storage volume into logical volumes.
Each persistent filesystem except the boot filesystems uses an LVM logical volume.
One LUKS2 container encrypts the LVM physical volume.

## Size configuration

The policy file is `storage/layout.json`.
It defines default sizes, minimum sizes, allocation weights, and mount restrictions.
The minimum supported disk budget is 24 GB.

The renderer also accepts `--disk-size-gb`.
The value changes the fixed allocation budget for that image.
The generated manifest records the exact virtual disk size in bytes.

Operate this example on the build host.
The command creates a smaller lab layout with the same filesystem scheme.
Use a new output directory for each layout.

```sh
python3 -m balboa render --flavor laptop --lab --disk-size-gb 24 --output build/laptop-24gb
```

For production, omit `--disk-size-gb` to retain the 128 GB policy.
If a different size receives approval, supply that size explicitly.
The renderer does not derive sizes from the physical disk capacity.

The installer rejects a disk that cannot contain the fixed partitions.
On a larger disk, the installer leaves the excess space unallocated.
No partition or logical volume uses the Kickstart `--grow` flag.

## Filesystem scheme

All flavors use the same persistent filesystem scheme.
Test images use the same volume names, encryption boundary, and mount restrictions.
Only the fixed volume sizes change.

| Filesystem | Purpose | Mount restrictions |
| --- | --- | --- |
| `/` | System programs | Defaults |
| `/home` | User files | `nodev,nosuid` |
| `/tmp` | Temporary files | `nodev,nosuid,noexec` |
| `/var` | Variable application data | `nodev,nosuid` |
| `/var/tmp` | Persistent temporary files | `nodev,nosuid,noexec` |
| `/var/log` | System logs | `nodev,nosuid,noexec` |
| `/var/log/audit` | Security audit logs | `nodev,nosuid,noexec` |
| Swap | Memory overflow | Encrypted LVM volume |

The `nodev` flag prevents device files from supplying device access.
The `nosuid` flag prevents file permissions from elevating program privileges.
The `noexec` flag prevents direct program execution from that filesystem.

The root filesystem permits program execution.
The home filesystem permits development tools and local applications.
The variable data filesystem permits package installation scripts and application requirements.

The installer creates the required BIOS or UEFI boot partitions outside LVM.
The `/boot` filesystem also remains outside LVM.
It has a fixed 2048 MiB size with `nodev,nosuid,noexec` restrictions.
Boot filesystems remain unencrypted so that firmware and GRUB can start the system.

## Allocation method

The renderer reserves 3072 MiB for boot partitions and alignment.
MiB means 1,048,576 bytes.
The renderer reserves another 256 MiB for encryption metadata and LVM overhead.

Each logical volume first receives its minimum size.
The renderer divides the remaining budget according to the policy weights.
Rounding differences remain in the root allocation.

LVM rounds requested sizes to its allocation units.
The reserved overhead permits this rounding without enlarging the physical volume.
The manifest records requested sizes in MiB.

The default requested allocations use these sizes:

| Logical volume | Production 128 GB, MiB | Lab 32 GB, MiB |
| --- | --- | --- |
| Root | 36999 | 11365 |
| Home | 29827 | 4192 |
| Temporary | 4626 | 964 |
| Variable data | 19531 | 4882 |
| Persistent temporary | 4626 | 964 |
| Logs | 11311 | 2155 |
| Audit logs | 6684 | 1191 |
| Swap | 5138 | 1476 |

The separate log and audit volumes limit interference with the root filesystem.
They still require capacity alerts and site retention rules.
The layout does not replace a workload capacity assessment.
