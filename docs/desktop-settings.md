# Desktop Settings

The laptop and workstation use the same GNOME defaults.
Files (Nautilus) supplies the file picker for Appearance → Add Picture.
The Rocky DVD package for Files requires `tracker-miners`.
That package supplies the Search Locations settings.
The server omits these desktop packages. [GNOME file picker source](https://github.com/GNOME/xdg-desktop-portal-gnome/blob/47.3/src/filechooser.c) · [GNOME Search Locations help](https://help.gnome.org/gnome-help/search-filesystem-locations.html)

## Search and privacy defaults

GNOME disables Lock Screen Notifications and App Search by default.
App Search controls results from applications in the Activities overview.
GNOME still lets you find installed applications by name.

The installer masks `tracker-miner-fs-3.service` for all users to prevent background file indexing.
A mask prevents systemd from starting a service.
Use Search Locations to select folders for later use with the indexer.

GNOME enables Automatically Delete Temporary Files in Privacy & Security → File History & Trash by default.
GNOME uses its standard age limit of 30 days.
The installer sets these desktop defaults in `/etc/dconf/db/local.d/00-balboa`.

## Online Accounts

An account provider connects GNOME to a specific service.
The installer sets `enable=none` in the `[providers]` section of `/etc/goa.conf`.
GNOME Online Accounts offers no provider types with this value.
To permit a provider later, replace `none` with the provider identifier.
After you change the file, end your session.
Start a new session.

## Test results

The package test resolves Files and `tracker-miners` from the locked Rocky DVD for both desktop flavors.
In QEMU, Add Picture accepts a test image and Search Locations opens while Tracker is inactive.
GNOME shows the notification, search, and cleanup defaults, and the Online Accounts list is empty.
