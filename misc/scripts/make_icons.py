#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Generates the executable icons with build status badges, as well as the console variants for Windows.
# For windows, download latest GTK runtime:
# - https://github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer/releases
# pip install cairosvg pillow icnsutil
# For generating badges:
# - https://danmarshall.github.io/google-font-to-svg-path/
# - use Lilita One, size 100px
# - transform it in godsvg to proper size


import io
from dataclasses import dataclass, replace
from os import mkdir
from shutil import copytree
from typing import Dict, List

from cairosvg.parser import Tree
from cairosvg.surface import SVGSurface
from icnsutil import ArgbImage, IcnsFile, IcnsType
from PIL import Image, ImageFile


@dataclass(frozen=True)
class badge_dimensions:
    x: int
    y: int
    height: int
    pos_reverse: bool = False


@dataclass(frozen=True)
class badge_descriptor:
    svg_bytes: bytes = bytes()
    dimensions: badge_dimensions = badge_dimensions(0, 0, 0)


@dataclass(frozen=True)
class android_icon_descriptor:
    size: int
    foreground_size: int
    foreground_contents_size: int
    badges: List[badge_descriptor]


status_badge_dimensions_by_size = {
    512: badge_dimensions(x=10, y=10, height=128),  # macos
    256: badge_dimensions(x=10, y=10, height=64),  # win32, macos
    192: badge_dimensions(x=0, y=0, height=64),  # android
    144: badge_dimensions(x=0, y=0, height=48),  # android
    128: badge_dimensions(x=10, y=10, height=32),  # win32, macos
    96: badge_dimensions(x=0, y=0, height=32),  # android
    72: badge_dimensions(x=0, y=0, height=24),  # android
    64: badge_dimensions(x=0, y=0, height=16),  # win32
    48: badge_dimensions(x=0, y=0, height=16),  # win32, android
    32: badge_dimensions(x=0, y=0, height=11),  # win32, macos
    16: badge_dimensions(x=0, y=0, height=6),  # win32, macos
}

platform_path = "../../platform"
icon_path = "../../icon.svg"
icon_components_path = "../dist/icon_generation"


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


def rasterize_svg(icon_svg_bytes: bytes, icon_size: int) -> ImageFile:
    return Image.open(io.BytesIO(load_svg(icon_svg_bytes, height=icon_size).cairo.write_to_png(target=None)))


def assemble_icon_image(base_icon_image: ImageFile, badges: List[badge_descriptor]) -> ImageFile:
    icon_result = base_icon_image.copy()

    for badge_descriptor in badges:
        badge_png = rasterize_svg(badge_descriptor.svg_bytes, badge_descriptor.dimensions.height)

        badge_pos = (
            (
                icon_result.width - badge_png.width - badge_descriptor.dimensions.x,
                icon_result.height - badge_png.height - badge_descriptor.dimensions.y,
            )
            if badge_descriptor.dimensions.pos_reverse
            else (badge_descriptor.dimensions.x, badge_descriptor.dimensions.y)
        )
        icon_result.alpha_composite(badge_png, badge_pos)
    return icon_result


def compose_windows_icon(build_status: str, out_path: str, is_console: bool = False):
    base_icon_svg_bytes = load_file(icon_path)

    # Not including biggest ones (512, 1024) or it blows up in size
    sizes: List[int] = [256, 128, 64, 48, 32, 16]
    icon_badges: Dict[int, List[badge_descriptor]] = {s: [] for s in sizes}

    if build_status in ["dev", "beta", "rc"]:
        build_status_badge_svg_bytes = load_file(f"{icon_components_path}/icon_badges/status_{build_status}.svg")
        build_status_badge_mini_svg_bytes = load_file(
            f"{icon_components_path}/icon_badges/status_{build_status}_mini.svg"
        )

        icon_badges[256].append(badge_descriptor(build_status_badge_svg_bytes, status_badge_dimensions_by_size[256]))
        icon_badges[128].append(badge_descriptor(build_status_badge_svg_bytes, status_badge_dimensions_by_size[128]))
        icon_badges[64].append(badge_descriptor(build_status_badge_svg_bytes, status_badge_dimensions_by_size[64]))
        icon_badges[48].append(badge_descriptor(build_status_badge_svg_bytes, status_badge_dimensions_by_size[48]))
        icon_badges[32].append(badge_descriptor(build_status_badge_svg_bytes, status_badge_dimensions_by_size[32]))
        icon_badges[16].append(badge_descriptor(build_status_badge_mini_svg_bytes, status_badge_dimensions_by_size[16]))

    if is_console:
        console_badge_svg_bytes = load_file(f"{icon_components_path}/icon_badges/console.svg")

        icon_badges[256].append(
            badge_descriptor(console_badge_svg_bytes, badge_dimensions(x=10, y=10, height=80, pos_reverse=True))
        )
        icon_badges[128].append(
            badge_descriptor(console_badge_svg_bytes, badge_dimensions(x=10, y=10, height=40, pos_reverse=True))
        )
        icon_badges[64].append(
            badge_descriptor(console_badge_svg_bytes, badge_dimensions(x=0, y=0, height=24, pos_reverse=True))
        )
        icon_badges[48].append(
            badge_descriptor(console_badge_svg_bytes, badge_dimensions(x=0, y=0, height=17, pos_reverse=True))
        )
        icon_badges[32].append(
            badge_descriptor(console_badge_svg_bytes, badge_dimensions(x=0, y=0, height=13, pos_reverse=True))
        )
        icon_badges[16].append(
            badge_descriptor(console_badge_svg_bytes, badge_dimensions(x=0, y=0, height=8, pos_reverse=True))
        )

    images: List[ImageFile] = []
    for size, badges in icon_badges.items():
        image = assemble_icon_image(rasterize_svg(base_icon_svg_bytes, size), badges)
        images.append(image)

    images[0].save(
        out_path,
        append_images=images[1:],
        sizes=[(im.width, im.height) for im in images],
    )


def compose_android_icons(build_status: str, out_base_path: str):
    try_mkdir(out_base_path)
    base_icon_svg_bytes = load_file(icon_path)

    icon_descriptors: Dict[str, android_icon_descriptor] = {
        "mdpi": android_icon_descriptor(
            size=(int)(48), foreground_size=(int)(108), foreground_contents_size=(int)(66), badges=[]
        ),
        "hdpi": android_icon_descriptor(
            size=(int)(1.5 * 48), foreground_size=(int)(1.5 * 108), foreground_contents_size=(int)(1.5 * 66), badges=[]
        ),
        "xhdpi": android_icon_descriptor(
            size=(int)(2 * 48), foreground_size=(int)(2 * 108), foreground_contents_size=(int)(2 * 66), badges=[]
        ),
        "xxhdpi": android_icon_descriptor(
            size=(int)(3 * 48), foreground_size=(int)(3 * 108), foreground_contents_size=(int)(3 * 66), badges=[]
        ),
        "xxxhdpi": android_icon_descriptor(
            size=(int)(4 * 48), foreground_size=(int)(4 * 108), foreground_contents_size=(int)(4 * 66), badges=[]
        ),
    }

    if build_status in ["dev", "beta", "rc"]:
        build_status_badge_svg_bytes = load_file(f"{icon_components_path}/icon_badges/status_{build_status}.svg")
        icon_descriptors["mdpi"].badges.append(
            badge_descriptor(
                build_status_badge_svg_bytes, status_badge_dimensions_by_size[icon_descriptors["mdpi"].size]
            )
        )
        icon_descriptors["hdpi"].badges.append(
            badge_descriptor(
                build_status_badge_svg_bytes, status_badge_dimensions_by_size[icon_descriptors["hdpi"].size]
            )
        )
        icon_descriptors["xhdpi"].badges.append(
            badge_descriptor(
                build_status_badge_svg_bytes, status_badge_dimensions_by_size[icon_descriptors["xhdpi"].size]
            )
        )
        icon_descriptors["xxhdpi"].badges.append(
            badge_descriptor(
                build_status_badge_svg_bytes, status_badge_dimensions_by_size[icon_descriptors["xxhdpi"].size]
            )
        )
        icon_descriptors["xxxhdpi"].badges.append(
            badge_descriptor(
                build_status_badge_svg_bytes, status_badge_dimensions_by_size[icon_descriptors["xxxhdpi"].size]
            )
        )

    for icon_size_name, descriptor in icon_descriptors.items():
        try_mkdir(f"{out_base_path}/mipmap-{icon_size_name}")
        image = assemble_icon_image(rasterize_svg(base_icon_svg_bytes, descriptor.size), descriptor.badges)
        image.save(f"{out_base_path}/mipmap-{icon_size_name}/icon.png")

        foreground_badges: List[badge_descriptor] = [badge_descriptor() for _ in range(len(descriptor.badges))]
        for i, fg_badge in enumerate(descriptor.badges):
            foreground_badges[i] = replace(
                fg_badge,
                dimensions=replace(
                    fg_badge.dimensions,
                    height=round(fg_badge.dimensions.height * descriptor.foreground_contents_size / descriptor.size),
                ),
            )
        image_foreground_contents = assemble_icon_image(
            rasterize_svg(base_icon_svg_bytes, descriptor.foreground_contents_size), foreground_badges
        )
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
    new_data = [(0, 0, 0, 0) for _ in range(len(pixel_data))]
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


def compose_macos_icons(build_status: str, out_base_path: str):
    # Icns contains only some sizes: https://iconhandbook.co.uk/reference/chart/osx/
    # Needs macos-compliant background which can't be plainly bundled in the repo,
    # so use the already provided godot icon and add some badges to it

    if build_status in ["dev", "beta", "rc"]:
        build_status_badge_svg_bytes = load_file(f"{icon_components_path}/icon_badges/status_{build_status}.svg")
        build_status_badge_mini_svg_bytes = load_file(
            f"{icon_components_path}/icon_badges/status_{build_status}_mini.svg"
        )

    try_mkdir(out_base_path)
    icns_file = IcnsFile(f"{icon_components_path}/macos/Godot.icns")
    for icon_key, icon_bytes in icns_file.media.items():
        icon_type = IcnsType.get(icon_key)
        if icon_type.is_type("argb"):
            icon_argb = ArgbImage(data=icon_bytes)
            icon_png = Image.new("RGBA", icon_argb.size)
            for y in range(icon_png.height):
                for x in range(icon_png.width):
                    i = y * icon_png.width + x
                    icon_png.putpixel((x, y), (icon_argb.r[i], icon_argb.g[i], icon_argb.b[i], icon_argb.a[i]))
        elif icon_type.is_type("png"):
            icon_png = Image.open(io.BytesIO(icon_bytes))
        else:
            continue

        badges = []
        if build_status in ["dev", "beta", "rc"]:
            if icon_type.desc.find("2x") != -1:
                base_size = icon_type.size[0] // 2
                dimensions = status_badge_dimensions_by_size[base_size]
                dimensions = replace(dimensions, x=dimensions.x * 2, y=dimensions.y * 2, height=dimensions.height * 2)
            else:
                base_size = icon_type.size[0]
                dimensions = status_badge_dimensions_by_size[base_size]
            badges.append(
                badge_descriptor(
                    build_status_badge_svg_bytes if base_size > 16 else build_status_badge_mini_svg_bytes, dimensions
                )
            )

        assembled_icon = assemble_icon_image(icon_png, badges)
        if icon_type.is_type("argb"):
            assembled_argb = ArgbImage(image=assembled_icon)
            assembled_icon_bytes = assembled_argb.argb_data()
        elif icon_type.is_type("png"):
            bytes_io = io.BytesIO()
            assembled_icon.save(bytes_io, format="PNG")
            assembled_icon_bytes = bytes_io.getvalue()
        icns_file.media[icon_key] = assembled_icon_bytes
    icns_file.write(f"{out_base_path}/Godot_{build_status}.icns")


try_mkdir(f"{platform_path}/android/icons")
try_mkdir(f"{platform_path}/macos/icons")
for build_status in ["beta", "rc", "dev", "stable"]:
    compose_windows_icon(build_status, f"{platform_path}/windows/icons/godot_{build_status}.ico")
    compose_windows_icon(
        build_status, f"{platform_path}/windows/icons/godot_console_{build_status}.ico", is_console=True
    )
    compose_android_icons(build_status, f"{platform_path}/android/icons/{build_status}")
    compose_macos_icons(build_status, f"{platform_path}/macos/icons")
