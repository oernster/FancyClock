"""Generate every platform icon asset from the master PNG.

The single source of truth for the app icon is ``fancyclock.png`` at the
repo root (a square 1024x1024 RGBA image). This script emits the full
platform set into ``assets/``:

* ``fancyclock_icon_<size>.png`` for each size in PNG_SIZES (hicolor set,
  favicons, installer badges);
* ``fancyclock_icon.png`` at the canonical badge size;
* ``fancyclock.ico`` (multi-size Windows icon);
* ``fancyclock.icns`` (macOS icon).

Run after changing the master: ``python generate_icons.py``.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parent
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


def load_master() -> Image.Image:
    """Load the master PNG as square RGBA, centre-cropping if needed."""
    if not MASTER_PNG.is_file():
        raise SystemExit(f"Master icon not found: {MASTER_PNG}")

    image = Image.open(MASTER_PNG).convert("RGBA")
    width, height = image.size
    if width != height:
        side = min(width, height)
        left = (width - side) // 2
        top = (height - side) // 2
        image = image.crop((left, top, left + side, top + side))
    return image


def main() -> int:
    master = load_master()
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
