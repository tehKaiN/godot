# For windows, download latest GTK runtime:
# - https://github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer/releases
# pip install cairosvg pillow
# For generating badges:
# - https://danmarshall.github.io/google-font-to-svg-path/
# - use Lilita One, size 100px
# - transform it in godsvg to proper size


import io
from dataclasses import dataclass

from cairosvg.parser import Tree
from cairosvg.surface import SVGSurface
from PIL import Image, ImageFile


@dataclass
class badge_descriptor:
    path: str
    x: int
    y: int
    pos_reverse: bool = False
    width: int | None = None
    height: int | None = None


def load_svg(path: str, width=None, height=None) -> SVGSurface:
    with open(path) as svg_file:
        svg_bytes = svg_file.read()
    svg = SVGSurface(
        Tree(bytestring=svg_bytes),
        output=None,
        dpi=72,  # FIXME: get rid of magic number
        output_width=width,
        output_height=height,
    )
    return svg


def assemble_icon_image(icon_path: str, icon_size: int, badges: list[badge_descriptor]) -> ImageFile:
    icon_png = Image.open(io.BytesIO(load_svg(icon_path, height=icon_size).cairo.write_to_png(target=None)))

    for badge_descriptor in badges:
        badge_png = Image.open(
            io.BytesIO(load_svg(badge_descriptor.path, height=badge_descriptor.height).cairo.write_to_png(target=None))
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
    base_icon_path = "../../icon.svg"

    sizes: list[int] = [256, 128, 64, 48, 32, 16]
    icon_badges: dict[int, list[badge_descriptor]] = {s: [] for s in sizes}

    if build_kind in ["dev", "beta", "rc"]:
        build_kind_badge_svg = f"icon_badges/status_{build_kind}.svg"
        build_kind_badge_mini_svg = f"icon_badges/status_{build_kind}_mini.svg"

        icon_badges[256].append(badge_descriptor(build_kind_badge_svg, x=10, y=10, height=64))
        icon_badges[128].append(badge_descriptor(build_kind_badge_svg, x=10, y=10, height=32))
        icon_badges[64].append(badge_descriptor(build_kind_badge_svg, x=0, y=0, height=16))
        icon_badges[48].append(badge_descriptor(build_kind_badge_svg, x=0, y=0, height=16))
        icon_badges[32].append(badge_descriptor(build_kind_badge_svg, x=0, y=0, height=11))
        icon_badges[16].append(badge_descriptor(build_kind_badge_mini_svg, x=0, y=0, height=6))

    if is_console:
        console_badge_svg = "icon_badges/console.svg"

        icon_badges[256].append(badge_descriptor(console_badge_svg, x=10, y=10, height=80, pos_reverse=True))
        icon_badges[128].append(badge_descriptor(console_badge_svg, x=10, y=10, height=40, pos_reverse=True))
        icon_badges[64].append(badge_descriptor(console_badge_svg, x=0, y=0, height=24, pos_reverse=True))
        icon_badges[48].append(badge_descriptor(console_badge_svg, x=0, y=0, height=17, pos_reverse=True))
        icon_badges[32].append(badge_descriptor(console_badge_svg, x=0, y=0, height=13, pos_reverse=True))
        icon_badges[16].append(badge_descriptor(console_badge_svg, x=0, y=0, height=8, pos_reverse=True))

    images: list[ImageFile] = []
    for size, badges in icon_badges.items():
        image = assemble_icon_image(base_icon_path, size, badges)
        images.append(image)

    images[0].save(
        out_path,
        append_images=images[1:],
        sizes=[(im.width, im.height) for im in images],
    )


for build_kind in ["beta", "rc", "dev", "stable"]:
    compose_windows_icon(build_kind, f"icons/godot_{build_kind}.ico")
    compose_windows_icon(build_kind, f"icons/godot_console_{build_kind}.ico", is_console=True)
