# Desktop Settings

The laptop and workstation use the same GNOME defaults.
Files (Nautilus) supplies the file picker for Appearance → Add Picture.
The Rocky DVD package for Files requires `tracker-miners`, which supplies the Search Locations settings.
The server omits these desktop packages. [GNOME file picker source](https://github.com/GNOME/xdg-desktop-portal-gnome/blob/47.3/src/filechooser.c) · [GNOME Search Locations help](https://help.gnome.org/gnome-help/search-filesystem-locations.html)

## Search and privacy defaults

Lock Screen Notifications and App Search start off.
App Search controls results from applications in the Activities overview.
GNOME still lets you find installed applications by name.

The installer masks `tracker-miner-fs-3.service` for all users to prevent background file indexing.
A mask prevents systemd from starting a service.
Search Locations opens so that you can select folders for later use with the indexer.

Automatically Delete Temporary Files starts on in Privacy & Security → File History & Trash.
GNOME uses its standard age limit of 30 days.
The installer sets these desktop defaults in `/etc/dconf/db/local.d/00-balboa`.

## Online Accounts

An account provider connects GNOME to a specific service.
The installer sets `enable=none` in the `[providers]` section of `/etc/goa.conf`.
GNOME Online Accounts offers no provider types with this value.
To permit a provider later, replace `none` with the provider identifier.
Log out and log in again after you change the file.

## Test results

The package test resolves Files and `tracker-miners` from the locked Rocky DVD for both desktop flavors.
In QEMU, Add Picture accepts a test image and Search Locations opens while Tracker is inactive.
GNOME shows the notification, search, and cleanup defaults, and the Online Accounts list is empty.
