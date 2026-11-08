"""Create local branding assets from constrained text and repository graphics."""

from functools import lru_cache
from html import escape
import hashlib
import shutil
import struct
import subprocess

SIZES = {"boot.png": (1920, 1080), "wallpaper.png": (1920, 1080), "login.png": (960, 96)}
BOOT_DIR = "/boot/grub2/themes/balboa"
DESKTOP_DIR = "/usr/share/backgrounds/balboa"


def validate_text(text):
    if not isinstance(text, str) or not 1 <= len(text) <= 64 or not text.isprintable() or not text.strip():
        raise ValueError("The branding text requires 1 to 64 printable characters without line breaks.")


def logo(x, y, scale):
    return f'''<g transform="translate({x},{y}) scale({scale})">
<path d="M100 5 L185 54 V151 L100 200 L15 151 V54 Z" fill="#52dfbf"/>
<path d="M100 9 L181 56 V149 L100 196 L19 149 V56 Z" fill="#102938"/>
<path d="M39 139 L92 59 L124 107 L145 80 L169 139 Z" fill="#f1fafb"/>
<path d="M92 59 L109 139 H39 Z" fill="#52dfbf"/>
<path d="M109 139 L124 107 L145 80 L169 139 Z" fill="#5c94b5"/>
</g>'''


def label(text, x, y, size, width, color="#f1fafb"):
    size = min(size, width / (len(text) * 1.05))
    return (f'<text x="{x}" y="{y}" text-anchor="middle" font-family="DejaVu Sans" '
            f'font-size="{size}" fill="{color}">{escape(text)}</text>')


def vector(text, name):
    validate_text(text)
    width, height = SIZES[name]
    if name == "login.png":
        content = logo(462, 1, .18) + label(text, 480, 65, 26, 900)
        content += label("Powered by Rocky Linux", 480, 91, 20, 900, "#b8d4dc")
    else:
        content = '''<path d="M0 0 H1920 V1080 H0 Z" fill="#07121f"/>
<path d="M0 850 L430 430 L980 1080 H0 Z" fill="#102938"/>
<path d="M0 1080 L830 510 L1410 1080 Z" fill="#173a49"/>
<path d="M760 1080 L1480 330 L1920 820 V1080 Z" fill="#1d4352"/>
<path d="M1480 330 L1610 1080 H760 Z" fill="#183746"/>
<path d="M0 1078 H1920 V1080 H0 Z" fill="#52dfbf"/>'''
        if name == "boot.png":
            content += logo(850, 220, 1.1) + label(text, 960, 520, 52, 1600)
        else:
            content += logo(1250, 560, 1.1) + label(text, 1360, 850, 44, 650)
            content += '<path d="M1255 888 H1465 V891 H1255 Z" fill="#52dfbf"/>'
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">{content}</svg>'


@lru_cache(maxsize=8)
def images(text):
    validate_text(text)
    tool = shutil.which("magick") or shutil.which("convert")
    if not tool:
        raise ValueError("Install ImageMagick and the DejaVu Sans font on the render host.")
    result = {}
    for name, dimensions in SIZES.items():
        converted = subprocess.run([tool, "-background", "none", "svg:-", "-strip", "png32:-"],
                                   input=vector(text, name).encode(), capture_output=True)
        data = converted.stdout
        if converted.returncode or data[:8] != b"\x89PNG\r\n\x1a\n" or len(data) < 24:
            raise ValueError("ImageMagick cannot create the branding images. Install SVG support and the DejaVu Sans font.")
        if struct.unpack(">II", data[16:24]) != dimensions:
            raise ValueError("The generated branding image has incorrect dimensions.")
        result[name] = data
    return result


def record(text):
    return {"text": text, "images": {name: {"width": SIZES[name][0], "height": SIZES[name][1],
                                           "sha256": hashlib.sha256(data).hexdigest()}
                                    for name, data in images(text).items()}}


GRUB_THEME = '''desktop-image: "boot.png"
title-text: ""
terminal-font: "Unifont Regular 16"
+ boot_menu {
  left = 15%
  top = 63%
  width = 70%
  height = 28%
  item_color = "#b8d4dc"
  selected_item_color = "#52dfbf"
  item_height = 32
  item_padding = 8
  item_spacing = 4
}
'''
