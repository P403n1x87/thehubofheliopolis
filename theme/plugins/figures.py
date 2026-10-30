# -*- coding: utf-8 -*-
"""
Figures
=======

Rewrite the rendered HTML of articles and pages so that the theme does not have
to patch it up in the browser:

- every image is wrapped in a link to the full-size file;
- an image followed by an emphasised caption in the same paragraph, i.e.

      ![alt](src){: .center-image }
      *Caption*

  becomes a <figure> with a <figcaption>;
- a code block followed by a paragraph made only of an emphasised line, i.e.

      :::nasm
      ...

  *hello64.asm*

  becomes a <figure class="code"> whose caption is shown as the block's title.
"""

from bs4 import BeautifulSoup
from bs4 import NavigableString
from pelican import contents
from pelican import signals


def _children(tag):
    """The child nodes of a tag, ignoring whitespace-only strings."""
    return [
        c for c in tag.contents if not (isinstance(c, NavigableString) and not c.strip())
    ]


def _link_images(soup):
    for img in soup.find_all("img"):
        if img.parent.name == "a" or not img.get("src"):
            continue

        link = soup.new_tag("a", href=img["src"], target="_blank", rel="noopener")
        img.wrap(link)

        p = link.parent
        if p.name != "p":
            continue

        children = _children(p)
        if len(children) == 2 and children[0] is link and children[1].name == "em":
            caption = soup.new_tag("figcaption")
            caption.extend(list(children[1].contents))
            figure = soup.new_tag("figure")
            p.replace_with(figure)
            figure.append(link)
            figure.append(caption)


def _caption_code(soup):
    for block in soup.select("div.highlight, table.highlighttable"):
        if block.find_parent("table", class_="highlighttable"):
            continue

        p = block.find_next_sibling()
        if p is None or p.name != "p":
            continue

        children = _children(p)
        if len(children) != 1 or children[0].name != "em":
            continue

        caption = soup.new_tag("figcaption")
        caption.extend(list(children[0].contents))
        figure = soup.new_tag("figure", attrs={"class": "code"})
        block.wrap(figure)
        figure.insert(0, caption)
        p.decompose()


def figures(content):
    if isinstance(content, contents.Static) or not content._content:
        return

    soup = BeautifulSoup(content._content, "html.parser")
    _link_images(soup)
    _caption_code(soup)
    content._content = soup.decode()


def register():
    signals.content_object_init.connect(figures)
