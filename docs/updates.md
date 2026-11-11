# Desktop package updates

DNF Automatic installs security updates on the laptop and workstation.
A security advisory identifies packages that address known vulnerabilities.
DNF installs the updates and their required dependencies from the enabled RPM repositories.
The desktop uses DNF for package search, installation, and repository control.

The timer uses the Rocky schedule at 06:00 local time with up to one hour of delay.
It can start a missed run after the system starts again.
The service waits for initial hardening and the first assessment to finish.
The service also waits until initial hardening releases the DVD repository restriction.
The update configuration leaves restarts under operator control.

## Operate the update timer

Use the generic `dnf-automatic.timer` on the installed desktop.
This timer uses `/etc/dnf/automatic.conf` for update selection and installation.
The other DNF Automatic timers override parts of that configuration.
Use these commands on the installed desktop to see the schedule and results.

```sh
systemctl list-timers dnf-automatic.timer
sudo journalctl -u dnf-automatic.service
sudo dnf history info last
```

To pause future updates, disable the timer on the installed desktop.
To resume updates, enable the timer.

```sh
sudo systemctl disable --now dnf-automatic.timer
sudo systemctl enable --now dnf-automatic.timer
```

Use `sudoedit /etc/dnf/automatic.conf` to change the update policy.
Set `apply_updates = no` to download security updates for review.
Use `sudo systemctl edit dnf-automatic.timer` to change the schedule.

The security filter uses advisory data from the repositories.
Use `sudo dnf upgrade --refresh` to review all pending updates, including releases without advisories.
Review the proposed transaction before you accept it.
Do later security assessments through the maintenance procedure. [Maintenance](maintenance.md#update-installed-systems)

## Control repositories

Operate `dnf repolist --all` on the installed desktop to see the repository identifiers and states.
Use `dnf config-manager` to save a repository state.
For example, these commands disable EPEL and then enable it again on the laptop.

```sh
sudo dnf config-manager --set-disabled epel
sudo dnf config-manager --set-enabled epel
```

Use the identifier from `dnf repolist --all` for another repository.
DNF Automatic reads the same enabled repositories and package exclusions as DNF.
Use `dnf search` or `dnf repoquery` to find packages.
Use `fwupdmgr get-updates` on the laptop to see available firmware updates.

## Migrate an existing desktop

1. Open a terminal in a copy of this repository on the installed Balboa desktop.
2. Complete initial hardening and the first assessment.
3. If the desktop already uses DNF Automatic, examine its configuration before you replace it.
4. Install the tools.
5. Configure the security update policy.

```sh
sudo dnf --disablerepo='*' --enablerepo=baseos,appstream install dnf-automatic dnf-plugins-core
sudo install -m 0644 guest/dnf-automatic.conf /etc/dnf/automatic.conf
sudo install -D -m 0644 guest/dnf-automatic-guard.conf /etc/systemd/system/dnf-automatic.service.d/60-balboa-guard.conf
sudo restorecon -v /etc/dnf/automatic.conf /etc/systemd/system/dnf-automatic.service.d/60-balboa-guard.conf
```

Review the removal transaction before you accept it.
The `--noautoremove` option retains other dependencies, including `fwupd` on the laptop.

```sh
sudo dnf remove --noautoremove gnome-software PackageKit PackageKit-glib flatpak flatpak-libs flatpak-selinux flatpak-session-helper
```

After removal completes, reload the service configuration.
Start the timer.

```sh
sudo systemctl daemon-reload
sudo systemctl enable --now dnf-automatic.timer
```

See [DNF Automatic](https://dnf.readthedocs.io/en/latest/automatic.html) for update options.
See [DNF config-manager](https://dnf-plugins-core.readthedocs.io/en/latest/config_manager.html) for repository options.
