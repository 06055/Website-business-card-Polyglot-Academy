"""Build the site's logo and favicons from the supplied artwork - no redrawing.

Two sources of truth, both exactly as delivered by the owner:

    brand/own_book.png   the shield emblem (owl, book, star, laurels) -> the header logo
    brand/icon_own.png   the owl's head on a navy tile -> favicon, app icons

Everything here is mechanical: crop the empty background, resize, round the corners, write PNG and
ICO. Pillow is a build-time tool only, never a dependency of the site:

    uv run --no-project --with pillow python brand/make_icons.py
"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
BRAND = Path(__file__).resolve().parent
ICONS = ROOT / "static" / "icons"

HEADER_SOURCE = BRAND / "own_book.png"
ICON_SOURCE = BRAND / "icon_own.png"
# Measured: the gold artwork inside each file, the rest being background margin.
EMBLEM = (93, 38, 547, 576)         # the shield in own_book.png (640x640)
OWL = (48, 207, 1206, 938)          # the owl's head in icon_own.png (1254x1254)
RADIUS_RATIO = 0.178
SUPERSAMPLE = 4


def square(box, padding=0.0):
    """The smallest square around `box`, grown by `padding`, centred on it."""
    left, top, right, bottom = box
    cx, cy = (left + right) / 2, (top + bottom) / 2
    half = max(right - left, bottom - top) * (1 + padding) / 2
    return round(cx - half), round(cy - half), round(cx + half), round(cy + half)


def rounded_mask(size, radius):
    """A rounded-square alpha mask, drawn large and shrunk down so the curve stays smooth."""
    big = Image.new("L", (size * SUPERSAMPLE, size * SUPERSAMPLE), 0)
    ImageDraw.Draw(big).rounded_rectangle(
        (0, 0, size * SUPERSAMPLE - 1, size * SUPERSAMPLE - 1), radius=radius * SUPERSAMPLE, fill=255)
    return big.resize((size, size), Image.LANCZOS)


def icon(image, size, transparent_corners=True):
    """`image` at `size`, with rounded corners cut out (or filled in behind it)."""
    flat = image.resize((size, size), Image.LANCZOS)
    if size <= 48:
        # Below ~48 px the eyes and the pages lose their edges to the resampling; this restores them.
        flat = flat.filter(ImageFilter.UnsharpMask(radius=1, percent=60, threshold=0))
    if not transparent_corners:
        return flat
    out = flat.convert("RGBA")
    out.putalpha(rounded_mask(size, size * RADIUS_RATIO))
    return out


def fill_corners(image):
    """Extend the artwork over its own rounded corners: the nearest pixel, mirrored outwards.

    Apple draws its home-screen icons on black wherever they are transparent, and its mask is a
    little wider than these corners, so the corners are filled rather than cut out.
    """
    out = image.copy()
    pixels = out.load()
    size = out.width
    radius = size * RADIUS_RATIO
    for cx, cy, x_range, y_range in (
            (radius, radius, range(0, int(radius)), range(0, int(radius))),
            (size - radius, radius, range(int(size - radius), size), range(0, int(radius))),
            (radius, size - radius, range(0, int(radius)), range(int(size - radius), size)),
            (size - radius, size - radius, range(int(size - radius), size), range(int(size - radius), size))):
        for x in x_range:
            for y in y_range:
                dx, dy = x - cx, y - cy
                distance = (dx * dx + dy * dy) ** 0.5
                if distance <= radius - 1 or distance == 0:
                    continue
                scale = (radius - 1) / distance
                pixels[x, y] = pixels[round(cx + dx * scale), round(cy + dy * scale)]
    return out


def save(image, name, palette=True, **kwargs):
    """Write the icon, as a palette PNG where that costs nothing visible (a fraction of the bytes)."""
    path = ICONS / name
    if palette:
        image = image.quantize(colors=255, method=Image.FASTOCTREE, dither=Image.FLOYDSTEINBERG)
    image.save(path, optimize=True, **kwargs)
    print(f"{path.relative_to(ROOT)}  {image.size[0]}x{image.size[1]}  {path.stat().st_size / 1024:.1f} KB")


def main():
    # Both artworks come with a wide background margin, and at 48 px in the header or 16 px in a tab
    # that margin is what makes the drawing small. So each one is cropped back to its own artwork with
    # a thin safe padding. Nothing is redrawn, moved or stretched - the same picture, closer up.
    header = Image.open(HEADER_SOURCE).convert("RGB").crop(square(EMBLEM, padding=0.06))
    owl = Image.open(ICON_SOURCE).convert("RGB").crop((31, 0, 1223, 1192))   # square(OWL) + 3%

    save(icon(header, 208), "polyglot-owl-logo.png")        # the header, up to 52 px at 4x
    save(fill_corners(icon(owl, 180, transparent_corners=False)), "apple-touch-icon.png")
    save(icon(owl, 192), "android-chrome-192x192.png")
    save(icon(owl, 512), "android-chrome-512x512.png")
    small = {size: icon(owl, size) for size in (16, 32, 48)}
    save(small[32], "favicon-32x32.png")
    save(small[16], "favicon-16x16.png")
    # Each image in the .ico is the one prepared for that size, not a blurry resize of the largest.
    save(small[48], "favicon.ico", palette=False, sizes=[(16, 16), (32, 32), (48, 48)],
         append_images=[small[16], small[32]])


if __name__ == "__main__":
    main()
