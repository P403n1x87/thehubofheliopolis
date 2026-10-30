import re
from pathlib import Path
from urllib.parse import unquote

from conftest import ROOT


EXTERNAL = re.compile(r"^(https?:|mailto:|data:|//)")


def test_build_produces_every_article(articles):
    sources = [
        source
        for source in (ROOT / "content").glob("*.md")
        if not re.search(r"^status:\s*(draft|hidden)\s*$", source.read_text(), re.I | re.M)
    ]
    assert sources
    assert len(articles) == len(sources)


def test_internal_links_resolve(site, pages):
    ids = {
        (site / path).resolve(): {t["id"] for t in soup.find_all(id=True)}
        for path, soup in pages.items()
    }

    broken = []
    for path, soup in pages.items():
        page = site / path
        for tag, attr in (("a", "href"), ("img", "src"), ("link", "href"), ("script", "src")):
            for element in soup.find_all(tag):
                url = element.get(attr)
                if not url or EXTERNAL.match(url):
                    continue

                target, _, fragment = url.partition("#")
                resolved = (page.parent / unquote(target)).resolve() if target else page.resolve()
                if resolved.is_dir():
                    resolved = resolved / "index.html"

                if not resolved.exists():
                    broken.append(f"{path}: {url}")
                elif fragment and resolved.suffix == ".html" and unquote(fragment) not in ids[resolved]:
                    broken.append(f"{path}: {url} (no such anchor)")

    assert not broken, "\n".join(broken)


def test_articles_show_read_time(articles):
    missing = [
        path
        for path, soup in articles.items()
        if not re.search(r"\b\d+ min read\b", soup.select_one(".meta").get_text())
    ]
    assert not missing


def test_toc_is_moved_to_the_sidebar(articles):
    with_toc = sum(
        "[TOC]" in source.read_text() for source in (ROOT / "content").glob("*.md")
    )
    in_sidebar = [path for path, soup in articles.items() if soup.select_one(".aside details.toc")]
    left_inline = [path for path, soup in articles.items() if soup.select_one(".entry-content .toc")]

    assert len(in_sidebar) == with_toc
    assert not left_inline, left_inline


def test_figures_are_well_formed(articles):
    bad = []
    for path, soup in articles.items():
        for figure in soup.select(".entry-content figure"):
            if "code" in (figure.get("class") or []):
                ok = figure.select_one(":scope > figcaption") and figure.select_one(":scope > .highlight")
            else:
                ok = figure.select_one(":scope > a > img")
            if not ok:
                bad.append(f"{path}: {figure.decode()[:80]}")
    assert not bad, "\n".join(bad)


def test_images_link_to_full_size(articles):
    unlinked = [
        f"{path}: {img.get('src')}"
        for path, soup in articles.items()
        for img in soup.select(".entry-content img")
        if img.parent.name != "a"
    ]
    assert not unlinked, "\n".join(unlinked)
