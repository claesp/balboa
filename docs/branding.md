# Boot and desktop images

The render command creates three PNG images.
PNG is a format for image files.
The boot image and wallpaper use a fixed Unsplash mountain photo.
All three images show a geometric logo and your text below it.

The render host requires ImageMagick with SVG support, Fontconfig, and `grub2-mkfont` or `grub-mkfont`.
The repository supplies the Inter font files.
Image generation operates locally without network access.
SVG is a format for vector graphics.
ImageMagick converts generated SVG graphics into PNG files.

## Set the text

Set the optional `branding_text` field in your site JSON file.
The default text is `Balboa`.
The field accepts 1 to 64 printable characters without line breaks.

Use this field in your complete site file:

```json
"branding_text": "Example Systems"
```

Operate the render command from the repository root on the build host.
Use a new output directory.
The installer erases the disk that you select.

```sh
python3 -m balboa render --flavor laptop --site site.json --disk nvme0n1 --output build/laptop-branded
```

To override the site text, add `--branding-text "Example Systems"` to the render command.
The flag also works with `--lab`.
The renderer treats the text as literal image text.

## Generated files

The render output contains these three images:

| File under the output directory | Size | Installed purpose |
| --- | --- | --- |
| `branding/boot.png` | 1920 × 1080 | Background for GRUB and Plymouth |
| `branding/wallpaper.png` | 2560 × 1440 | Default GNOME wallpaper |
| `branding/login.png` | 640 × 180 | Logo banner for the GNOME login screen |

All flavors generate all three files for review.
The server installs only the boot image.
The workstation and laptop install all three images.

The login image includes the exact phrase `Powered by Rocky Linux`.
The login banner has a transparent background.
Only the logo and text remain visible over the GDM background.
GDM shows the image in its logo area.

The renderer embeds the images into the Kickstart file.
The ISO build does not require separate image copies.
A digest identifies file contents.
The manifest records the image dimensions, text, and SHA256 digests.

## Installed behavior

GRUB shows the boot image behind its menu for two seconds.
Plymouth reuses that image after the kernel starts.
See [Boot process](boot.md) for the spinner, disk prompt, and text fallback.
The installer ISO retains its official boot menu.

The boot theme resides in `/boot/grub2/themes/balboa/`.
The theme uses graphics output when the firmware supplies it.
A system without graphics cannot show an image.

The GNOME images reside in `/usr/share/backgrounds/balboa/`.
The default wallpaper applies to light and dark modes.
Users can change their wallpaper after login.

The GDM login screen uses its supported logo configuration.
GDM is the GNOME service that shows the login screen.
The custom image occupies the logo banner area.

The login configuration retains the security database and the vendor defaults.
The images do not change the account password policy.
The LUKS passphrase accepts 5 to 128 printable characters.

## Source assets and fonts

The photo shows Giau Pass at sunset.
The [Unsplash source page](https://unsplash.com/photos/aerial-view-of-mountains-during-sunset-8Nql6oVT_1A) identifies the selected photo.
The image uses the [Unsplash License](https://unsplash.com/license).

The source photo resides in `assets/photos/giau-pass.jpg`.
The official Inter 4.1 font resides in `assets/fonts/Inter-Regular.ttf`.
The repository retains its license in `assets/fonts/OFL.txt`.

The source record is `assets/sources.json`.
The renderer requires matching source digests before image generation.
It crops each photo to fill its target dimensions and applies a dark overlay for text contrast.

The renderer uses a private font configuration for Inter.
It does not require a system-wide Inter installation on the build host.
It also generates `branding/inter.pf2` for GRUB text.
That bitmap uses the Inter glyphs with the converted family name `BalboaBoot`.

The installed graphical interfaces use Inter.
These interfaces include the generated images, GRUB, Plymouth, GNOME, and GDM.
Firmware screens, text consoles, and terminal grids retain their native or fixed-width fonts.

## References

The [GRUB manual](https://www.gnu.org/software/grub/manual/grub/html_node/Simple-configuration.html) describes graphics output and themes.
The [Red Hat GNOME guide](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/10/html/administering_rhel_by_using_the_gnome_desktop_environment/customizing-desktop-appearance-and-branding) describes wallpaper defaults and the GDM logo.
These references describe the interfaces that Balboa uses.
