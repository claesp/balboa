"""Create local branding assets from constrained text and repository graphics."""

from functools import lru_cache
from html import escape
import hashlib
import json
import os
from pathlib import Path
import tempfile
import shutil
import struct
import subprocess

ROOT = Path(__file__).resolve().parent.parent
PHOTO = ROOT / "assets/photos/giau-pass.jpg"
FONT = ROOT / "assets/fonts/Inter-Regular.ttf"
SIZES = {"boot.png": (1920, 1080), "wallpaper.png": (2560, 1440), "login.png": (640, 180)}
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
    return (f'<text x="{x}" y="{y}" text-anchor="middle" font-family="Inter" '
            f'font-size="{size}" fill="{color}">{escape(text)}</text>')


def vector(text, name):
    validate_text(text)
    width, height = SIZES[name]
    if name == "login.png":
        content = logo(292, 10, .28) + label(text, 320, 113, 28, 560)
        content += label("Powered by Rocky Linux", 320, 149, 18, 560, "#b8d4dc")
        view = "0 0 640 180"
    else:
        content = ""
        if name == "boot.png":
            content += logo(850, 220, 1.1) + label(text, 960, 520, 52, 1600)
        else:
            content += logo(1420, 730, .6) + label(text, 1480, 920, 30, 370)
        view = "0 0 1920 1080"
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="{view}">{content}</svg>'


def sources():
    record = json.loads((ROOT / "assets/sources.json").read_text())
    for name, path in (("photo", PHOTO), ("font", FONT)):
        if hashlib.sha256(path.read_bytes()).hexdigest() != record[name]["sha256"]:
            raise ValueError("The branding photo or font does not match assets/sources.json.")
    return record


@lru_cache(maxsize=1)
def grub_font():
    sources()
    tool = shutil.which("grub2-mkfont") or shutil.which("grub-mkfont")
    if not tool:
        raise ValueError("Install grub2-mkfont or grub-mkfont on the render host.")
    with tempfile.TemporaryDirectory(prefix="balboa-font-") as directory:
        output = Path(directory) / "inter.pf2"
        subprocess.run([tool, "--size=18", "--name=BalboaBoot", "--output=" + str(output), str(FONT)],
                       check=True, capture_output=True)
        data = output.read_bytes()
    if not data.startswith(b"FILE\x00\x00\x00\x04PFF2"):
        raise ValueError("The generated GRUB font has an incorrect format.")
    return data


@lru_cache(maxsize=8)
def images(text):
    validate_text(text)
    tool = shutil.which("magick") or shutil.which("convert")
    if not tool:
        raise ValueError("Install ImageMagick with SVG support on the render host.")
    sources()
    result = {}
    with tempfile.TemporaryDirectory(prefix="balboa-fontconfig-") as directory:
        configuration = Path(directory) / "fonts.conf"
        configuration.write_text(f'<fontconfig><dir>{escape(str(FONT.parent))}</dir>'
                                 f'<cachedir>{escape(directory)}/cache</cachedir></fontconfig>')
        environment = {**os.environ, "FONTCONFIG_FILE": str(configuration)}
        if not shutil.which("fc-match"):
            raise ValueError("Install Fontconfig on the render host.")
        resolved = subprocess.run(["fc-match", "-f", "%{file}", "Inter"], capture_output=True,
                                  text=True, check=True, env=environment).stdout
        if Path(resolved).resolve() != FONT.resolve():
            raise ValueError("Fontconfig cannot find the bundled Inter font.")
        for name, dimensions in SIZES.items():
            width, height = dimensions
            shade = "B8" if name == "boot.png" else "85" if name == "login.png" else "35"
            converted = subprocess.run([
                tool, str(PHOTO), "-auto-orient", "-resize", f"{width}x{height}^",
                "-gravity", "center", "-extent", f"{width}x{height}",
                "-fill", "#07121f" + shade, "-draw", f"rectangle 0,0 {width},{height}",
                "(", "-background", "none", "svg:-", ")", "-compose", "over", "-composite",
                "-strip", "-define", "png:compression-level=9", "png32:-"],
                input=vector(text, name).encode(), capture_output=True, env=environment)
            data = converted.stdout
            if converted.returncode or data[:8] != b"\x89PNG\r\n\x1a\n" or len(data) < 24:
                raise ValueError("ImageMagick cannot create the branding images. Install SVG support.")
            if struct.unpack(">II", data[16:24]) != dimensions:
                raise ValueError("The generated branding image has incorrect dimensions.")
            result[name] = data
    return result


def record(text):
    return {"text": text, "sources": sources(), "grub_font_sha256": hashlib.sha256(grub_font()).hexdigest(), "images": {name: {"width": SIZES[name][0], "height": SIZES[name][1],
                                           "sha256": hashlib.sha256(data).hexdigest()}
                                    for name, data in images(text).items()}}


GRUB_THEME = '''desktop-image: "boot.png"
title-text: ""
terminal-font: "BalboaBoot Regular 18"
+ boot_menu {
  left = 15%
  top = 63%
  width = 70%
  height = 28%
  item_font = "BalboaBoot Regular 18"
  selected_item_font = "BalboaBoot Regular 18"
  item_color = "#b8d4dc"
  selected_item_color = "#52dfbf"
  item_height = 32
  item_padding = 8
  item_spacing = 4
}
'''
