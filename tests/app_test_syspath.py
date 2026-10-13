"""Tests that the sys.path bootstrap block is present in all app entry-point files."""

import ast
from pathlib import Path
import sys
import pytest

# Files that must contain the repo-root sys.path bootstrap.
_REPO_ROOT = Path(__file__).resolve().parent.parent
APP_FILES = [
    _REPO_ROOT / "app" / "main.py",
    _REPO_ROOT / "app" / "pages" / "2_Reference_Review.py",
    _REPO_ROOT / "app" / "pages" / "3_Compare_Versions.py",
    _REPO_ROOT / "app" / "pages" / "4_Changed_Decisions.py",
    _REPO_ROOT / "app" / "pages" / "5_Decision.py",
    _REPO_ROOT / "app" / "pages" / "6_Export.py",
]


@pytest.mark.parametrize("app_file", APP_FILES, ids=[f.name for f in APP_FILES])
def test_syspath_block_present(app_file: Path) -> None:
    """Assert each app file has the sys.path bootstrap before any app./gate. import."""
    source = app_file.read_text(encoding="utf-8")

    # The sentinel comment must be present.
    assert "sys.path.insert" in source, (
        f"{app_file.name}: missing sys.path.insert – the repo-root bootstrap block "
        "is required so Streamlit can find app.* and gate.* packages."
    )

    # The block must appear BEFORE the first 'from app.' or 'from gate.' line.
    lines = source.splitlines()
    syspath_line = next(i for i, l in enumerate(lines) if "sys.path.insert" in l)
    first_app_import = next(
        (i for i, l in enumerate(lines) if l.startswith("from app.") or l.startswith("from gate.")),
        len(lines),
    )
    assert syspath_line < first_app_import, (
        f"{app_file.name}: sys.path.insert (line {syspath_line+1}) must come "
        f"before the first app./gate. import (line {first_app_import+1})."
    )


def test_repo_root_resolves_correctly_for_main() -> None:
    """Assert _REPO_ROOT in main.py resolves to the actual repo root."""
    main_py = _REPO_ROOT / "app" / "main.py"
    source = main_py.read_text(encoding="utf-8")
    # main.py uses parent.parent (app/main.py -> app/ -> repo root)
    assert "parent.parent" in source
    # pages use parent.parent.parent
    for page in APP_FILES[1:]:
        page_src = page.read_text(encoding="utf-8")
        assert "parent.parent.parent" in page_src, (
            f"{page.name}: pages must use __file__.parent.parent.parent to reach repo root"
        )
