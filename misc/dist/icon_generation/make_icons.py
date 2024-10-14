# For windows, download latest GTK runtime:
# - https://github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer/releases
# pip install cairosvg pillow
# For generating badges:
# - https://danmarshall.github.io/google-font-to-svg-path/
# - use Lilita One, size 100px
# - transform it in godsvg to proper size


import io
import re
from os import mkdir
from shutil import copytree
from dataclasses import dataclass

from cairosvg.parser import Tree
from cairosvg.surface import SVGSurface
from PIL import Image, ImageFile


@dataclass
class badge_descriptor:
    svg_bytes: bytes
    x: int
    y: int
    pos_reverse: bool = False
    width: int | None = None
    height: int | None = None

@dataclass
class android_icon_descriptor:
    size: int
    foreground_size: int
    foreground_contents_size: int
    badges: list[badge_descriptor]

def load_file(path: str) -> bytes:
    with open(path) as svg_file:
        svg_bytes = svg_file.read()
        return svg_bytes.encode()

def load_svg(svg_bytes: bytes, width=None, height=None) -> SVGSurface:
    svg = SVGSurface(
        Tree(bytestring=svg_bytes),
        output=None,
        dpi=72,  # FIXME: get rid of magic number
        output_width=width,
        output_height=height,
    )
    return svg

def try_mkdir(dir: str) -> bool:
    try:
        mkdir(dir)
        return True
    except:
        return False


def assemble_icon_image(icon_svg_bytes: bytes, icon_size: int, badges: list[badge_descriptor]) -> ImageFile:
    icon_png = Image.open(io.BytesIO(load_svg(icon_svg_bytes, height=icon_size).cairo.write_to_png(target=None)))

    for badge_descriptor in badges:
        badge_png = Image.open(
            io.BytesIO(load_svg(badge_descriptor.svg_bytes, height=badge_descriptor.height).cairo.write_to_png(target=None))
        )

        badge_pos = (
            (
                icon_png.width - badge_png.width - badge_descriptor.x,
                icon_png.height - badge_png.height - badge_descriptor.y,
            )
            if badge_descriptor.pos_reverse
            else (badge_descriptor.x, badge_descriptor.y)
        )
        icon_png.alpha_composite(badge_png, badge_pos)
    return icon_png


def compose_windows_icon(build_kind: str, out_path: str, is_console: bool = False):
    base_icon_svg_bytes = load_file("../../../icon.svg")

    sizes: list[int] = [256, 128, 64, 48, 32, 16]
    icon_badges: dict[int, list[badge_descriptor]] = {s: [] for s in sizes}

    if build_kind in ["dev", "beta", "rc"]:
        build_kind_badge_svg_bytes = load_file(f"icon_badges/status_{build_kind}.svg")
        build_kind_badge_mini_svg_bytes = load_file(f"icon_badges/status_{build_kind}_mini.svg")

        icon_badges[256].append(badge_descriptor(build_kind_badge_svg_bytes, x=10, y=10, height=64))
        icon_badges[128].append(badge_descriptor(build_kind_badge_svg_bytes, x=10, y=10, height=32))
        icon_badges[64].append(badge_descriptor(build_kind_badge_svg_bytes, x=0, y=0, height=16))
        icon_badges[48].append(badge_descriptor(build_kind_badge_svg_bytes, x=0, y=0, height=16))
        icon_badges[32].append(badge_descriptor(build_kind_badge_svg_bytes, x=0, y=0, height=11))
        icon_badges[16].append(badge_descriptor(build_kind_badge_mini_svg_bytes, x=0, y=0, height=6))

    if is_console:
        console_badge_svg_bytes = load_file("icon_badges/console.svg")

        icon_badges[256].append(badge_descriptor(console_badge_svg_bytes, x=10, y=10, height=80, pos_reverse=True))
        icon_badges[128].append(badge_descriptor(console_badge_svg_bytes, x=10, y=10, height=40, pos_reverse=True))
        icon_badges[64].append(badge_descriptor(console_badge_svg_bytes, x=0, y=0, height=24, pos_reverse=True))
        icon_badges[48].append(badge_descriptor(console_badge_svg_bytes, x=0, y=0, height=17, pos_reverse=True))
        icon_badges[32].append(badge_descriptor(console_badge_svg_bytes, x=0, y=0, height=13, pos_reverse=True))
        icon_badges[16].append(badge_descriptor(console_badge_svg_bytes, x=0, y=0, height=8, pos_reverse=True))

    images: list[ImageFile] = []
    for size, badges in icon_badges.items():
        image = assemble_icon_image(base_icon_svg_bytes, size, badges)
        images.append(image)

    images[0].save(
        out_path,
        append_images=images[1:],
        sizes=[(im.width, im.height) for im in images],
    )

def compose_android_icons(out_base_path: str):
    try_mkdir(out_base_path)
    base_icon_svg_bytes = load_file("../../../icon.svg")

    icon_descriptors: dict[str, android_icon_descriptor] = {
        'mdpi': android_icon_descriptor(size=(int)(48), foreground_size=(int)(108), foreground_contents_size=(int)(66), badges=[]),
        'hdpi': android_icon_descriptor(size=(int)(1.5*48), foreground_size=(int)(1.5*108), foreground_contents_size=(int)(1.5*66), badges=[]),
        'xhdpi': android_icon_descriptor(size=(int)(2*48), foreground_size=(int)(2*108), foreground_contents_size=(int)(2*66), badges=[]),
        'xxhdpi': android_icon_descriptor(size=(int)(3*48), foreground_size=(int)(3*108), foreground_contents_size=(int)(3*66), badges=[]),
        'xxxhdpi': android_icon_descriptor(size=(int)(4*48), foreground_size=(int)(4*108), foreground_contents_size=(int)(4*66), badges=[])}

    if build_kind in ["dev", "beta", "rc"]:
        build_kind_badge_svg_bytes = load_file(f"icon_badges/status_{build_kind}.svg")
        icon_descriptors['mdpi'].badges.append(badge_descriptor(build_kind_badge_svg_bytes, x=0, y=0, height=16))
        icon_descriptors['hdpi'].badges.append(badge_descriptor(build_kind_badge_svg_bytes, x=0, y=0, height=24))
        icon_descriptors['xhdpi'].badges.append(badge_descriptor(build_kind_badge_svg_bytes, x=0, y=0, height=32))
        icon_descriptors['xxhdpi'].badges.append(badge_descriptor(build_kind_badge_svg_bytes, x=0, y=0, height=48))
        icon_descriptors['xxxhdpi'].badges.append(badge_descriptor(build_kind_badge_svg_bytes, x=0, y=0, height=64))

    for icon_size_name, descriptor in icon_descriptors.items():
        try_mkdir(f"{out_base_path}/mipmap-{icon_size_name}")
        image = assemble_icon_image(base_icon_svg_bytes, descriptor.size, descriptor.badges)
        image.save(f"{out_base_path}/mipmap-{icon_size_name}/icon.png")

        foreground_badges = descriptor.badges[:]
        for fg_badge in foreground_badges:
            fg_badge.height = round(fg_badge.height * descriptor.foreground_contents_size / descriptor.size)
        image_foreground_contents = assemble_icon_image(base_icon_svg_bytes, descriptor.foreground_contents_size, foreground_badges)
        image_foreground = Image.new("RGBA", [descriptor.foreground_size, descriptor.foreground_size], (0, 0, 0, 0))
        foreground_margin_size = (descriptor.foreground_size - descriptor.foreground_contents_size) // 2
        image_foreground.paste(image_foreground_contents, (foreground_margin_size, foreground_margin_size))
        image_foreground.save(f"{out_base_path}/mipmap-{icon_size_name}/icon_foreground.png")

        image_background = Image.new("RGB", [descriptor.foreground_size, descriptor.foreground_size], "#32516b")
        image_background.save(f"{out_base_path}/mipmap-{icon_size_name}/icon_background.png")

    copytree(f"{out_base_path}/mipmap-mdpi", f"{out_base_path}/mipmap", dirs_exist_ok=True)

    # TODO: badge interior pixels are semi-transparent and probably shouldn't be - figure out a better way to mix white and alpha
    image_mono = Image.open(f"{out_base_path}/mipmap-mdpi/icon_foreground.png")
    pixel_data = image_mono.getdata()
    new_data = [0 for _ in range(len(pixel_data))]
    max_alpha = 0
    for i, pixel in enumerate(pixel_data):
        max_channel = min(pixel[0], pixel[1], pixel[2])
        alpha = min(pixel[3], 255 - max_channel)
        max_alpha = max(max_alpha, alpha)
        new_data[i] = (255, 255, 255, alpha)
    for i in range(len(new_data)):
        new_data[i] = (255, 255, 255, (int)((255 * new_data[i][3]) / max_alpha))
    image_mono.putdata(new_data)
    image_mono.save(f"{out_base_path}/mipmap/icon_monochrome.png")

for build_kind in ["beta", "rc", "dev", "stable"]:
    compose_windows_icon(build_kind, f"../../../platform/windows/icons/godot_{build_kind}.ico")
    compose_windows_icon(build_kind, f"../../../platform/windows/icons/godot_console_{build_kind}.ico", is_console=True)

try_mkdir("../../../platform/android/icons")
for build_kind in ["beta", "rc", "dev", "stable"]:
    compose_android_icons(f"../../../platform/android/icons/{build_kind}")
