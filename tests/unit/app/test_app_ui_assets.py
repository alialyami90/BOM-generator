"""The desktop app's UI files: complete, offline and in step with the M9 design (ADR 0011, 0015)."""

import re
from pathlib import Path

import pytest

from bomgen.app.window import INDEX, UI_DIR

REPO = Path(__file__).parents[3]
DESIGN = REPO / "docs" / "ui"
UI_FILES = sorted(p for p in UI_DIR.rglob("*") if p.is_file())
TEXT_FILES = [p for p in UI_FILES if p.suffix in {".html", ".css", ".js"}]
# Fetches a resource from the network: an attribute, a CSS url() or @import, or fetch().
REMOTE = re.compile(
    r"""(?:src|href)\s*=\s*["']?(?:https?:)?//|url\(\s*["']?(?:https?:)?//|@import|fetch\(""",
    re.IGNORECASE,
)


def index_references() -> list[str]:
    html = INDEX.read_text(encoding="utf-8")
    return re.findall(r"""(?:src|href)="([^"#][^"]*)\"""", html)


def test_index_loads_only_files_that_exist_in_the_ui_folder() -> None:
    references = index_references()

    assert references
    for reference in references:
        assert (UI_DIR / reference).is_file(), reference


def test_every_script_in_the_ui_folder_is_loaded() -> None:
    scripts = {p.name for p in UI_DIR.glob("*.js")}

    assert scripts == {r for r in index_references() if r.endswith(".js")}


@pytest.mark.parametrize("path", TEXT_FILES, ids=lambda p: p.name)
def test_ui_never_loads_anything_from_the_network(path: Path) -> None:
    assert not REMOTE.findall(path.read_text(encoding="utf-8"))


def test_fonts_come_from_the_ui_folder() -> None:
    css = (UI_DIR / "styles.css").read_text(encoding="utf-8")
    fonts = re.findall(r"""url\("(fonts/[^"]+)"\)""", css)

    assert len(fonts) == 2
    for font in fonts:
        assert (UI_DIR / font).is_file()


def test_tokens_match_the_design() -> None:
    # Regenerate in docs/ui (node docs/ui/tools/build-tokens.mjs), then copy here.
    design = DESIGN / "prototype" / "tokens.css"
    assert (UI_DIR / "tokens.css").read_bytes() == design.read_bytes()


@pytest.mark.parametrize("font", sorted((DESIGN / "fonts").iterdir()), ids=lambda p: p.name)
def test_fonts_and_licences_match_the_design(font: Path) -> None:
    assert (UI_DIR / "fonts" / font.name).read_bytes() == font.read_bytes()


def test_prototype_state_controls_are_not_in_the_app() -> None:
    for path in TEXT_FILES:
        text = path.read_text(encoding="utf-8")
        assert "Prototype states" not in text, path.name
        assert "proto-panel" not in text, path.name
