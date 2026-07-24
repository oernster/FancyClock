"""Generate every platform icon asset from the master PNG.

The single source of truth for the app artwork is ``fancyclock_plain.png``
at the repo root (a square 1024x1024 RGBA image with no badge). This script
first composites the red alarm-bell badge onto that clean master and writes
the result to ``fancyclock.png`` (the badged master every consumer uses),
then emits the full platform set into ``assets/``:

* ``fancyclock_icon_<size>.png`` for each size in PNG_SIZES (hicolor set,
  favicons, installer badges);
* ``fancyclock_icon.png`` at the canonical badge size;
* ``fancyclock.ico`` (multi-size Windows icon);
* ``fancyclock.icns`` (macOS icon).

Run after changing the plain master: ``python generate_icons.py``.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

PROJECT_ROOT = Path(__file__).resolve().parent
PLAIN_MASTER_PNG = PROJECT_ROOT / "fancyclock_plain.png"
MASTER_PNG = PROJECT_ROOT / "fancyclock.png"
ASSETS_DIR = PROJECT_ROOT / "assets"

PNG_SIZES = (16, 24, 32, 48, 64, 96, 128, 256, 512, 1024)
ICO_SIZES = (16, 24, 32, 48, 64, 128, 256)
CANONICAL_PNG_SIZE = 256
ICNS_SOURCE_SIZE = 1024

PNG_NAME_TEMPLATE = "fancyclock_icon_{size}.png"
CANONICAL_PNG_NAME = "fancyclock_icon.png"
ICO_NAME = "fancyclock.ico"
ICNS_NAME = "fancyclock.icns"

RESAMPLE = Image.Resampling.LANCZOS

# Alarm-bell badge (approved design): red roundel with a tilted white bell
# in the top-right corner of the 1024 canvas, first step toward the
# upcoming alarm-control feature.
SUPERSAMPLE = 4
BADGE_RADIUS = 190
BADGE_MARGIN = 24
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


def load_plain_master() -> Image.Image:
    """Load the plain master PNG as square RGBA, centre-cropping if needed."""
    if not PLAIN_MASTER_PNG.is_file():
        raise SystemExit(f"Plain master icon not found: {PLAIN_MASTER_PNG}")

    image = Image.open(PLAIN_MASTER_PNG).convert("RGBA")
    width, height = image.size
    if width != height:
        side = min(width, height)
        left = (width - side) // 2
        top = (height - side) // 2
        image = image.crop((left, top, left + side, top + side))
    return image


def build_badged_master() -> Image.Image:
    """Composite the alarm badge onto the plain master and write fancyclock.png."""
    master = load_plain_master()
    badge = build_badge(BADGE_RADIUS)

    out = master.copy()
    cx = out.width - BADGE_RADIUS - BADGE_MARGIN
    cy = BADGE_RADIUS + BADGE_MARGIN
    out.alpha_composite(badge, (cx - BADGE_RADIUS, cy - BADGE_RADIUS))

    out.save(MASTER_PNG)
    print(f"  {MASTER_PNG.name} (badged master)")
    return out


def main() -> int:
    master = build_badged_master()
    ASSETS_DIR.mkdir(exist_ok=True)

    for size in PNG_SIZES:
        out = ASSETS_DIR / PNG_NAME_TEMPLATE.format(size=size)
        master.resize((size, size), RESAMPLE).save(out)
        print(f"  {out.name}")

    canonical = ASSETS_DIR / CANONICAL_PNG_NAME
    master.resize((CANONICAL_PNG_SIZE, CANONICAL_PNG_SIZE), RESAMPLE).save(canonical)
    print(f"  {canonical.name}")

    ico_path = ASSETS_DIR / ICO_NAME
    largest = max(ICO_SIZES)
    master.resize((largest, largest), RESAMPLE).save(
        ico_path, format="ICO", sizes=[(s, s) for s in ICO_SIZES]
    )
    print(f"  {ico_path.name} (sizes {', '.join(str(s) for s in ICO_SIZES)})")

    icns_path = ASSETS_DIR / ICNS_NAME
    master.resize((ICNS_SOURCE_SIZE, ICNS_SOURCE_SIZE), RESAMPLE).save(
        icns_path, format="ICNS"
    )
    print(f"  {icns_path.name}")

    print(f"\nGenerated icon set in {ASSETS_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
