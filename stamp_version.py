"""Stamp the canonical version into the gh-pages site, which cannot read it.

The VERSION file at the repo root is the single source of truth. The runtime
(fancyclock.version) and packaging (pyproject.toml dynamic version, the build
scripts) all read it directly. Static assets under docs/ are served as-is by
GitHub Pages and cannot, so this script rewrites the version into them from
VERSION instead.

The docs/ tree is the ONLY target. Markdown at the repo root carries no version
data at all, by policy, so it is deliberately out of scope: a version in a
tracked document is a value that silently goes stale; the site is the one place
that has no other way to learn it.

Two things are stamped, both under docs/:

* delimited tokens ``<!--VERSION-->x.y.z<!--/VERSION-->`` in HTML or markdown,
  for visible version text;
* the JSON-LD ``"softwareVersion": "x.y.z"`` field in HTML, where an HTML
  comment token would corrupt the embedded JSON.

It is idempotent (stamping an already-current file changes nothing) and prints
the files it touched. buildexe.py, buildinstaller.py and builddmg.py call main()
so a release can never ship a site whose version disagrees with VERSION.
"""

from __future__ import annotations

import re
from pathlib import Path

VERSION_FILENAME = "VERSION"
FALLBACK_VERSION = "0.0.0-dev"
DOCS_DIRNAME = "docs"

_TOKEN_PATTERN = re.compile(r"(<!--VERSION-->)(.*?)(<!--/VERSION-->)", re.DOTALL)
_SOFTWARE_VERSION_PATTERN = re.compile(r'("softwareVersion"\s*:\s*")([^"]*)(")')


def read_version(root: Path) -> str:
    """Return the canonical version from the VERSION file (or a dev sentinel)."""
    version_file = root / VERSION_FILENAME
    if version_file.exists():
        return version_file.read_text(encoding="utf-8").strip()
    return FALLBACK_VERSION


def _stamp_text(text: str, version: str, *, is_html: bool) -> str:
    """Return ``text`` with every version token and JSON-LD field set to version."""
    stamped = _TOKEN_PATTERN.sub(lambda m: f"{m.group(1)}{version}{m.group(3)}", text)
    if is_html:
        stamped = _SOFTWARE_VERSION_PATTERN.sub(
            lambda m: f"{m.group(1)}{version}{m.group(3)}", stamped
        )
    return stamped


def _target_files(root: Path) -> list[Path]:
    """Collect the gh-pages files that carry a stamped version.

    Only the docs/ tree is stamped. Root markdown is never touched.
    """
    docs_dir = root / DOCS_DIRNAME
    if not docs_dir.is_dir():
        return []
    return [*docs_dir.rglob("*.html"), *docs_dir.rglob("*.md")]


def stamp(root: Path, version: str) -> list[Path]:
    """Stamp ``version`` into every target file; return the ones that changed."""
    touched: list[Path] = []
    for path in _target_files(root):
        original = path.read_text(encoding="utf-8")
        stamped = _stamp_text(original, version, is_html=path.suffix.lower() == ".html")
        if stamped != original:
            path.write_text(stamped, encoding="utf-8")
            touched.append(path)
    return touched


def main() -> int:
    """Stamp the gh-pages site from VERSION and report what changed."""
    root = Path(__file__).resolve().parent
    version = read_version(root)
    touched = stamp(root, version)
    if touched:
        print(f"Stamped version {version} into {len(touched)} file(s):")
        for path in touched:
            print(f"  {path.relative_to(root)}")
    else:
        print(f"Version {version} already current across {DOCS_DIRNAME}/.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
