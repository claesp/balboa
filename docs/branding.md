# Boot and desktop images

The render command creates three PNG images.
PNG is a format for image files.
The images contain a geometric mountain logo and your text below it.

The render host requires ImageMagick with SVG support and the DejaVu Sans font.
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
| `branding/boot.png` | 1920 × 1080 | Background for the installed GRUB menu |
| `branding/wallpaper.png` | 1920 × 1080 | Default GNOME wallpaper |
| `branding/login.png` | 960 × 96 | Logo banner for the GNOME login screen |

All flavors generate all three files for review.
The server installs only the boot image.
The workstation and laptop install all three images.

The login image includes the exact phrase `Powered by Rocky Linux`.
Its transparent background uses the login screen color.
GDM shows the image in its logo area.

The renderer embeds the images into the Kickstart file.
The ISO build does not require separate image copies.
A digest identifies file contents.
The manifest records the image dimensions, text, and SHA256 digests.

## Installed behavior

GRUB shows the boot image behind its menu for five seconds.
The image appears before the kernel starts.
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

## References

The [GRUB manual](https://www.gnu.org/software/grub/manual/grub/html_node/Simple-configuration.html) describes graphics output and themes.
The [Red Hat GNOME guide](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/10/html/administering_rhel_by_using_the_gnome_desktop_environment/customizing-desktop-appearance-and-branding) describes wallpaper defaults and the GDM logo.
These references describe the interfaces that Balboa uses.
