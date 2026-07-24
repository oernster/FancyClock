"""Structural tests enforcing the clean-architecture invariants.

These tests read source files with ``ast``; they never import the modules
they check, so they run without Qt.
"""

from __future__ import annotations

import ast
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PACKAGE_DIR = PROJECT_ROOT / "fancyclock"
TESTS_DIR = PROJECT_ROOT / "tests"

MAX_MODULE_LINES = 400
COMPOSITION_ROOT = PACKAGE_DIR / "main.py"

DOMAIN_ALLOWED_STDLIB = {"__future__", "dataclasses", "datetime", "typing", "math"}
APPLICATION_ALLOWED_STDLIB = DOMAIN_ALLOWED_STDLIB | {"pathlib"}

DOMAIN_FORBIDDEN_CALLS = ("datetime.now", "date.today", "datetime.utcnow")


def _modules(subdir: str) -> list[Path]:
    return sorted((PACKAGE_DIR / subdir).rglob("*.py"))


def _imports_of(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                found.add(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            found.add(node.module)
    return found


def _top_level(name: str) -> str:
    return name.split(".")[0]


def test_domain_is_pure() -> None:
    """Domain imports only a small stdlib whitelist and other domain code."""
    for module in _modules("domain"):
        for imported in _imports_of(module):
            if imported.startswith("fancyclock"):
                assert imported.startswith("fancyclock.domain"), (
                    f"{module.name} imports {imported}: domain may only "
                    "import domain"
                )
            else:
                assert _top_level(imported) in DOMAIN_ALLOWED_STDLIB, (
                    f"{module.name} imports {imported}: not in the domain "
                    "stdlib whitelist"
                )


def test_domain_never_reads_the_wall_clock() -> None:
    """Domain code never calls the wall clock directly."""
    for module in _modules("domain"):
        source = module.read_text(encoding="utf-8")
        for forbidden in DOMAIN_FORBIDDEN_CALLS:
            assert (
                f"{forbidden}(" not in source
            ), f"{module.name} calls {forbidden}(): inject time instead"


def test_application_depends_on_domain_only() -> None:
    """Application imports only domain, application and whitelisted stdlib."""
    for module in _modules("application"):
        for imported in _imports_of(module):
            if imported.startswith("fancyclock"):
                assert imported.startswith(
                    ("fancyclock.domain", "fancyclock.application")
                ), (
                    f"{module.name} imports {imported}: application may not "
                    "import infrastructure or ui"
                )
            else:
                assert _top_level(imported) in APPLICATION_ALLOWED_STDLIB, (
                    f"{module.name} imports {imported}: not in the "
                    "application stdlib whitelist"
                )


def test_infrastructure_never_imports_ui() -> None:
    """Infrastructure has no dependency on the UI layer."""
    for module in _modules("infrastructure"):
        for imported in _imports_of(module):
            assert not imported.startswith("fancyclock.ui"), (
                f"{module.name} imports {imported}: infrastructure may not " "import ui"
            )


def test_ui_never_imports_infrastructure() -> None:
    """The UI is a client of the application layer only."""
    for module in _modules("ui"):
        for imported in _imports_of(module):
            assert not imported.startswith("fancyclock.infrastructure"), (
                f"{module.name} imports {imported}: ui may not import " "infrastructure"
            )


def test_composition_root_is_the_only_infrastructure_consumer() -> None:
    """Only fancyclock/main.py wires infrastructure into the app."""
    for module in sorted(PACKAGE_DIR.rglob("*.py")):
        if module == COMPOSITION_ROOT:
            continue
        if module.is_relative_to(PACKAGE_DIR / "infrastructure"):
            continue
        for imported in _imports_of(module):
            assert not imported.startswith("fancyclock.infrastructure"), (
                f"{module.relative_to(PROJECT_ROOT)} imports {imported}: "
                "only the composition root may import infrastructure"
            )


def test_no_module_exceeds_the_line_limit() -> None:
    """App package and test modules stay at or below the module line limit."""
    for module in sorted(PACKAGE_DIR.rglob("*.py")) + sorted(TESTS_DIR.rglob("*.py")):
        lines = len(module.read_text(encoding="utf-8").splitlines())
        assert lines <= MAX_MODULE_LINES, (
            f"{module.relative_to(PROJECT_ROOT)} has {lines} lines "
            f"(limit {MAX_MODULE_LINES})"
        )
