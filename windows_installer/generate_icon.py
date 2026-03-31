"""
Generate ScreenDraw app icon (.ico) for Windows.
Creates a multi-size icon with the ScreenDraw logo.

Usage: python generate_icon.py
Requires: pip install pillow
"""

from PIL import Image, ImageDraw, ImageFont
import os

def create_icon():
    sizes = [16, 32, 48, 64, 128, 256]
    images = []

    for size in sizes:
        img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # Background circle - blue gradient feel
        margin = max(1, size // 16)
        draw.ellipse(
            [margin, margin, size - margin - 1, size - margin - 1],
            fill=(0, 122, 255, 255),
            outline=(0, 90, 200, 255),
            width=max(1, size // 32)
        )

        # Inner circle (lighter)
        inner_margin = size // 5
        draw.ellipse(
            [inner_margin, inner_margin, size - inner_margin, size - inner_margin],
            fill=(40, 140, 255, 255),
        )

        # Pen/pencil tip - a simple diagonal line with a dot
        cx, cy = size // 2, size // 2
        pen_len = size // 3
        # Diagonal stroke
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

        # Small "S" or "SD" text for larger sizes
        if size >= 64:
            try:
                font_size = size // 5
                try:
                    font = ImageFont.truetype("arial.ttf", font_size)
                except OSError:
                    try:
                        font = ImageFont.truetype("Arial.ttf", font_size)
                    except OSError:
                        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", font_size)
                bbox = draw.textbbox((0, 0), "SD", font=font)
                tw = bbox[2] - bbox[0]
                th = bbox[3] - bbox[1]
                draw.text(
                    (cx - tw // 2, cy + pen_len // 3),
                    "SD",
                    fill=(255, 255, 255, 220),
                    font=font,
                )
            except Exception:
                pass

        images.append(img)

    # Save as .ico
    output_path = os.path.join(os.path.dirname(__file__), "screendraw.ico")
    # ICO format: save the 256px version with all sizes embedded
    images[-1].save(
        output_path,
        format='ICO',
        sizes=[(s, s) for s in sizes],
        append_images=images[:-1],
    )
    print(f"Icon saved to: {output_path}")
    return output_path


if __name__ == "__main__":
    create_icon()
