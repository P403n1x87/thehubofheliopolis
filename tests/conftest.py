import subprocess
import sys
from pathlib import Path

import pytest
from bs4 import BeautifulSoup


ROOT = Path(__file__).resolve().parent.parent

sys.path.insert(0, str(ROOT / "theme" / "plugins"))


@pytest.fixture(scope="session")
def site(tmp_path_factory):
    """Build the site once into a temporary directory and return its path.

    Warnings are fatal, so a plugin that fails to load (e.g. because of a
    missing dependency) fails the build instead of being silently skipped.
    """
    output = tmp_path_factory.mktemp("output")
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pelican",
            "content",
            "-s",
            "pelicanconf.py",
            "-o",
            str(output),
            "--fatal",
            "warnings",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return output


@pytest.fixture(scope="session")
def pages(site):
    """Parsed HTML of every generated page, keyed by path relative to the site."""
    return {
        str(p.relative_to(site)): BeautifulSoup(p.read_text(), "html.parser")
        for p in site.rglob("*.html")
    }


@pytest.fixture(scope="session")
def articles(pages):
    return {
        path: soup
        for path, soup in pages.items()
        if "article" in (soup.body.get("class") or [])
    }
