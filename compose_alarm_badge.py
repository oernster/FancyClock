"""Compose a red alarm-bell badge onto the FancyClock master icon (preview)."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

MASTER = Path(r"C:\Users\Oliver\Development\FancyClock\fancyclock.png")
OUT_DIR = Path(__file__).parent

CANVAS = 1024
SUPERSAMPLE = 4

BADGE_RADIUS = 190
BADGE_CENTER = (CANVAS - BADGE_RADIUS - 24, BADGE_RADIUS + 24)

BADGE_RED = (225, 29, 46, 255)
BADGE_RED_DARK = (156, 14, 27, 255)
BELL_WHITE = (255, 255, 255, 255)
OUTLINE_FRACTION = 0.045
BELL_TILT_DEGREES = -14


def _draw_bell(size: int) -> Image.Image:
    """Draw a white bell glyph on a transparent square canvas."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    s = size
    cx = s / 2

    bell_w = 0.60 * s
    bw2 = bell_w / 2
    dome_top = 0.24 * s
    dome_base = dome_top + bw2
    body_bottom = 0.64 * s
    flare = 0.07 * s

    # Handle knob above the dome.
    knob_r = 0.055 * s
    d.ellipse(
        (cx - knob_r, dome_top - knob_r * 1.1, cx + knob_r, dome_top + knob_r * 0.9),
        fill=BELL_WHITE,
    )

    # Dome (top half circle).
    d.pieslice(
        (cx - bw2, dome_top, cx + bw2, dome_top + bell_w),
        start=180,
        end=360,
        fill=BELL_WHITE,
    )

    # Body flaring outwards to the rim.
    d.polygon(
        [
            (cx - bw2, dome_base),
            (cx - bw2 - flare, body_bottom),
            (cx + bw2 + flare, body_bottom),
            (cx + bw2, dome_base),
        ],
        fill=BELL_WHITE,
    )

    # Rim bar.
    rim_h = 0.055 * s
    rim_w2 = bw2 + flare + 0.035 * s
    d.rounded_rectangle(
        (cx - rim_w2, body_bottom, cx + rim_w2, body_bottom + rim_h),
        radius=rim_h / 2,
        fill=BELL_WHITE,
    )

    # Clapper.
    clap_r = 0.06 * s
    clap_cy = body_bottom + rim_h + clap_r * 0.9
    d.ellipse(
        (cx - clap_r, clap_cy - clap_r, cx + clap_r, clap_cy + clap_r),
        fill=BELL_WHITE,
    )

    return img.rotate(BELL_TILT_DEGREES, resample=Image.Resampling.BICUBIC)


def build_badge(radius: int) -> Image.Image:
    """Return the badge (red circle + white bell) at final resolution."""
    ss = radius * 2 * SUPERSAMPLE
    img = Image.new("RGBA", (ss, ss), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    outline = int(ss * OUTLINE_FRACTION / 2)
    d.ellipse((0, 0, ss - 1, ss - 1), fill=BADGE_RED_DARK)
    d.ellipse((outline, outline, ss - 1 - outline, ss - 1 - outline), fill=BADGE_RED)

    bell = _draw_bell(ss)
    img.alpha_composite(bell)

    return img.resize((radius * 2, radius * 2), Image.Resampling.LANCZOS)


def main() -> None:
    master = Image.open(MASTER).convert("RGBA")
    badge = build_badge(BADGE_RADIUS)

    out = master.copy()
    cx, cy = BADGE_CENTER
    out.alpha_composite(badge, (cx - BADGE_RADIUS, cy - BADGE_RADIUS))

    out.save(OUT_DIR / "fancyclock_alarm_1024.png")
    for size in (256, 64):
        out.resize((size, size), Image.Resampling.LANCZOS).save(
            OUT_DIR / f"fancyclock_alarm_{size}.png"
        )
    print("written:", OUT_DIR)


if __name__ == "__main__":
    main()
