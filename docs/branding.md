# Boot and desktop images

The render command creates three PNG images.
PNG is a format for image files.
The boot image and wallpaper use a fixed Unsplash photo from Abisko National Park in Sweden.
All three images show the configured name in large, light Inter Bold text.

The render host requires ImageMagick with SVG support, Fontconfig, and `grub2-mkfont` or `grub-mkfont`.
The repository supplies the Inter font files.
Image generation operates locally without network access.
SVG is a format for vector graphics.
ImageMagick converts generated SVG graphics into PNG files.

## Set the text

Set the optional `branding_text` field in your site JSON file.
The default text is `Balboa`.
The field accepts 1 to 64 printable characters without line breaks.

Use the following field in your complete site file.

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

The render command creates three images.

| File under the output directory | Size | Installed purpose |
| --- | --- | --- |
| `branding/boot.png` | 1920 × 1080 | Background for GRUB and Plymouth |
| `branding/wallpaper.png` | 2560 × 1440 | Default GNOME wallpaper |
| `branding/login.png` | 640 × 180 | Name banner for the GNOME login screen |

All flavors generate all three files for review.
The server installs only the boot image.
The workstation and laptop install all three images.

The login banner has a transparent background.
GDM shows the name over its own background in the logo area.
The name sits near the lower right of the wallpaper.
The boot image and wallpaper show the photo credit in the lower left corner.

If you enable graphical boot, the render command also writes `branding/plymouth/spinner.png` and `branding/plymouth/entry.png`.
Plymouth uses these images for the rotating ring and the disk password field.
The ring and the name use the same light foreground color.

The renderer places the images for installation in `balboa-files/`.
The ISO builder copies that directory onto the ISO.
A digest identifies file contents.
The manifest records the image dimensions, text, and SHA256 digests. [Add custom files](build.md#add-custom-files)

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
GNOME fits the full wallpaper to the screen to keep the credit visible.
Users can change their wallpaper after login.

The GDM login screen uses its supported logo configuration.
GDM is the GNOME service that shows the login screen.
The custom image occupies the logo banner area.

The login configuration retains the security database and the vendor defaults.
The images do not change the account password policy.
The renderer accepts a LUKS passphrase of 5 to 128 printable characters.

## Source assets and fonts

The photo by David Becker shows the northern lights over a lake.
The source is 3840 × 2544 pixels. [Unsplash source page](https://unsplash.com/photos/aurora-borealis-over-body-of-water-during-nighttime-58X3XfxxevU)
The image uses the Unsplash License. [License terms](https://unsplash.com/license)

The source photo resides in `assets/photos/abisko-aurora.jpg`.
The official Inter 4.1 fonts reside in `assets/fonts/Inter-Regular.ttf` and `assets/fonts/Inter-Bold.ttf`.
The renderer uses Inter Bold for the name and Inter Regular for the photo credit.
The repository retains its license in `assets/fonts/OFL.txt`.

The source record is `assets/sources.json`.
The renderer requires matching source digests before image generation.
The renderer crops the photo to fill each image and applies a dark overlay for text contrast.

The renderer uses a private font configuration for both Inter weights.
It does not require a system-wide Inter installation on the build host.
It also generates `branding/inter.pf2` for GRUB text.
That bitmap uses the Inter glyphs with the converted family name `BalboaBoot`.

The installed graphical interfaces use Inter.
These interfaces include the generated images, GRUB, Plymouth, GNOME, and GDM.
Firmware screens, text consoles, and terminal grids retain their native or fixed-width fonts.

## References

GRUB uses a theme to control graphics output. [GRUB manual](https://www.gnu.org/software/grub/manual/grub/html_node/Simple-configuration.html)
The Red Hat guide describes the GNOME wallpaper defaults and the GDM logo. [Red Hat GNOME guide](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/10/html/administering_rhel_by_using_the_gnome_desktop_environment/customizing-desktop-appearance-and-branding)
