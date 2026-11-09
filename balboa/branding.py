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
PHOTO = ROOT / "assets/photos/abisko-aurora.jpg"
FONT = ROOT / "assets/fonts/Inter-Regular.ttf"
BOLD_FONT = FONT.with_name("Inter-Bold.ttf")
FOREGROUND = "#f1fafb"
SIZES = {"boot.png": (1920, 1080), "wallpaper.png": (2560, 1440), "login.png": (640, 180)}
BOOT_DIR = "/boot/grub2/themes/balboa"
DESKTOP_DIR = "/usr/share/backgrounds/balboa"


def validate_text(text):
    if not isinstance(text, str) or not 1 <= len(text) <= 64 or not text.isprintable() or not text.strip():
        raise ValueError("The branding text requires 1 to 64 printable characters without line breaks.")


def label(text, x, y, size, width, anchor="middle", weight=700):
    size = min(size, width / (len(text) * 1.05))
    return (f'<text x="{x}" y="{y}" text-anchor="{anchor}" font-family="Inter" '
            f'font-weight="{weight}" font-size="{size}" fill="{FOREGROUND}">{escape(text)}</text>')


def vector(text, name, photo_credit):
    validate_text(text)
    width, height = SIZES[name]
    if name == "login.png":
        content = label(text, 320, 112, 72, 560)
        view = "0 0 640 180"
    else:
        if name == "boot.png":
            content = label(text, 960, 440, 120, 1440)
        else:
            content = label(text, 1780, 950, 92, 1380, anchor="end")
        content += label(photo_credit, 48, 1024, 28, 1080, anchor="start", weight=400)
        view = "0 0 1920 1080"
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="{view}">{content}</svg>'


def sources():
    record = json.loads((ROOT / "assets/sources.json").read_text())
    for name, path in (("photo", PHOTO), ("font", FONT), ("bold_font", BOLD_FONT)):
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


def image_tool():
    tool = shutil.which("magick") or shutil.which("convert")
    if not tool:
        raise ValueError("Install ImageMagick with SVG support on the render host.")
    return tool


def png(command, svg, dimensions, environment=None):
    converted = subprocess.run(command + ["-strip", "-define", "png:compression-level=9", "png32:-"],
                               input=svg.encode(), capture_output=True, env=environment)
    data = converted.stdout
    if converted.returncode or data[:8] != b"\x89PNG\r\n\x1a\n" or len(data) < 24:
        raise ValueError("ImageMagick cannot create the branding images. Install SVG support.")
    if struct.unpack(">II", data[16:24]) != dimensions:
        raise ValueError("The generated branding image has incorrect dimensions.")
    return data


@lru_cache(maxsize=1)
def plymouth_assets():
    command = [image_tool(), "-background", "none", "svg:-"]
    spinner = f'''<svg xmlns="http://www.w3.org/2000/svg" width="128" height="128" viewBox="0 0 128 128">
<g fill="none" stroke="{FOREGROUND}" stroke-width="10">
<circle cx="64" cy="64" r="49" stroke-opacity=".20"/>
<path d="M64 15 A49 49 0 0 1 110.04 80.76" stroke-opacity="1" stroke-linecap="round"/>
</g></svg>'''
    entry = f'''<svg xmlns="http://www.w3.org/2000/svg" width="460" height="52" viewBox="0 0 460 52">
<rect x="1" y="1" width="458" height="50" rx="11" fill="#07121f"
      stroke="{FOREGROUND}" stroke-opacity=".5" stroke-width="2"/>
</svg>'''
    return {"spinner.png": png(command, spinner, (128, 128)), "entry.png": png(command, entry, (460, 52))}


@lru_cache(maxsize=8)
def images(text):
    validate_text(text)
    tool = image_tool()
    photo_credit = sources()["photo"]["credit"]
    result = {}
    with tempfile.TemporaryDirectory(prefix="balboa-fontconfig-") as directory:
        configuration = Path(directory) / "fonts.conf"
        configuration.write_text(f'<fontconfig><dir>{escape(str(FONT.parent))}</dir>'
                                 f'<cachedir>{escape(directory)}/cache</cachedir></fontconfig>')
        environment = {**os.environ, "FONTCONFIG_FILE": str(configuration)}
        if not shutil.which("fc-match"):
            raise ValueError("Install Fontconfig on the render host.")
        resolved = subprocess.run(["fc-match", "-f", "%{file}", "Inter:style=Bold"], capture_output=True,
                                  text=True, check=True, env=environment).stdout
        if Path(resolved).resolve() != BOLD_FONT.resolve():
            raise ValueError("Fontconfig cannot find the bundled Inter Bold font.")
        for name, dimensions in SIZES.items():
            width, height = dimensions
            command = [tool, "-background", "none", "svg:-"]
            if name != "login.png":
                shade = "B8" if name == "boot.png" else "35"
                command = [
                    tool, str(PHOTO), "-auto-orient", "-resize", f"{width}x{height}^",
                    "-gravity", "center", "-extent", f"{width}x{height}",
                    "-fill", "#07121f" + shade, "-draw", f"rectangle 0,0 {width},{height}",
                    "(", "-background", "none", "svg:-", ")", "-compose", "over", "-composite"]
            result[name] = png(command, vector(text, name, photo_credit), dimensions, environment)
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
