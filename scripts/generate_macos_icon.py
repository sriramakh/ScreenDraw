#!/usr/bin/env python3
"""
Generate ScreenDraw app icon for macOS.
Creates:
  - .icns file for command-line builds (build.sh)
  - Individual PNGs for the Xcode asset catalog

Usage: python3 scripts/generate_macos_icon.py
Requires: pip3 install pillow
"""

import os
import subprocess
import tempfile
from PIL import Image, ImageDraw, ImageFont

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(SCRIPT_DIR)
ICONSET_DIR = os.path.join(ROOT_DIR, "ScreenDraw", "Assets.xcassets", "AppIcon.appiconset")
ICNS_OUTPUT = os.path.join(ROOT_DIR, "ScreenDraw", "AppIcon.icns")


def draw_icon(size):
    """Draw the ScreenDraw icon at the given pixel size."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Background: rounded-rect-ish circle (blue)
    margin = max(1, size // 16)
    draw.ellipse(
        [margin, margin, size - margin - 1, size - margin - 1],
        fill=(0, 122, 255, 255),
        outline=(0, 90, 200, 255),
        width=max(1, size // 32),
    )

    # Inner highlight circle
    inner = size // 5
    draw.ellipse(
        [inner, inner, size - inner, size - inner],
        fill=(40, 140, 255, 255),
    )

    # Pen stroke (diagonal white line)
    cx, cy = size // 2, size // 2
    pen_len = size // 3
    lw = max(1, size // 12)
    draw.line(
        [cx - pen_len // 2, cy + pen_len // 2, cx + pen_len // 2, cy - pen_len // 2],
        fill=(255, 255, 255, 255),
        width=lw,
    )

    # Pen tip dot
    tip_r = max(1, size // 16)
    tip_x = cx + pen_len // 2
    tip_y = cy - pen_len // 2
    draw.ellipse(
        [tip_x - tip_r, tip_y - tip_r, tip_x + tip_r, tip_y + tip_r],
        fill=(255, 255, 255, 255),
    )

    # "SD" text for larger sizes
    if size >= 64:
        try:
            font_size = size // 5
            font = None
            for path in [
                "/System/Library/Fonts/Helvetica.ttc",
                "/System/Library/Fonts/SFNSText.ttf",
                "/Library/Fonts/Arial.ttf",
            ]:
                if os.path.exists(path):
                    try:
                        font = ImageFont.truetype(path, font_size)
                        break
                    except OSError:
                        continue
            if font is None:
                font = ImageFont.load_default()

            bbox = draw.textbbox((0, 0), "SD", font=font)
            tw = bbox[2] - bbox[0]
            draw.text(
                (cx - tw // 2, cy + pen_len // 3),
                "SD",
                fill=(255, 255, 255, 220),
                font=font,
            )
        except Exception:
            pass

    return img


# macOS asset catalog required sizes: (point_size, scale) -> pixel_size
ASSET_CATALOG_SIZES = [
    (16, 1), (16, 2),
    (32, 1), (32, 2),
    (128, 1), (128, 2),
    (256, 1), (256, 2),
    (512, 1), (512, 2),
]


def generate_asset_catalog_pngs():
    """Generate PNGs for the Xcode asset catalog and update Contents.json."""
    os.makedirs(ICONSET_DIR, exist_ok=True)

    images_json = []
    for point_size, scale in ASSET_CATALOG_SIZES:
        pixel_size = point_size * scale
        if scale == 1:
            filename = f"icon_{point_size}x{point_size}.png"
        else:
            filename = f"icon_{point_size}x{point_size}@{scale}x.png"

        img = draw_icon(pixel_size)
        img.save(os.path.join(ICONSET_DIR, filename), "PNG")

        images_json.append({
            "filename": filename,
            "idiom": "mac",
            "scale": f"{scale}x",
            "size": f"{point_size}x{point_size}",
        })

    # Write Contents.json
    import json
    contents = {
        "images": images_json,
        "info": {"author": "xcode", "version": 1},
    }
    with open(os.path.join(ICONSET_DIR, "Contents.json"), "w") as f:
        json.dump(contents, f, indent=2)

    print(f"Asset catalog PNGs written to: {ICONSET_DIR}")


def generate_icns():
    """Generate .icns file using macOS iconutil."""
    with tempfile.TemporaryDirectory() as tmpdir:
        iconset_path = os.path.join(tmpdir, "AppIcon.iconset")
        os.makedirs(iconset_path)

        # iconutil expects specific filenames
        iconutil_sizes = [
            (16, 1), (16, 2),
            (32, 1), (32, 2),
            (128, 1), (128, 2),
            (256, 1), (256, 2),
            (512, 1), (512, 2),
        ]

        for point_size, scale in iconutil_sizes:
            pixel_size = point_size * scale
            if scale == 1:
                name = f"icon_{point_size}x{point_size}.png"
            else:
                name = f"icon_{point_size}x{point_size}@2x.png"

            img = draw_icon(pixel_size)
            img.save(os.path.join(iconset_path, name), "PNG")

        # Use iconutil to create .icns
        subprocess.run(
            ["iconutil", "-c", "icns", iconset_path, "-o", ICNS_OUTPUT],
            check=True,
        )
        print(f"ICNS file written to: {ICNS_OUTPUT}")


if __name__ == "__main__":
    print("Generating macOS app icons...")
    generate_asset_catalog_pngs()
    generate_icns()
    print("Done!")
