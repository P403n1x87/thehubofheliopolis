# -*- coding: utf-8 -*-
"""
Revisions
=========

Keep a dated log of the changes made to an article after it was published.
Each revision is a line of the ``Revisions`` metadata field, in the form
``YYYY-MM-DD: description``, where the description can use inline Markdown,
e.g.

    Revisions: 2026-11-06: Mention the [acknowledgement](https://example.com).
               2026-11-10: Fix a typo.

The revisions are exposed to the templates as ``article.revisions``, newest
first, each with a ``date``, a ``locale_date`` and the rendered ``html`` of the
description. Unless the article sets ``Modified`` explicitly, the date of the
latest revision also becomes its modified date, so the "updated" label and the
feeds stay in sync with the log.

A block of text changed by a revision can be marked with the revision's date,
using the attribute list syntax, i.e.

    This paragraph was rewritten.
    {: data-revision="2026-11-06" }

The marked block gets a note in its margin that shows the description of that
revision when hovered or focused, with a link to the revision log. To keep the
original wording and explain what changed since, follow the marked block with
the text of the update, marked with the ``revision-update`` class, i.e.

    This is what I originally wrote.
    {: data-revision="2026-11-06" }

    This is what has changed since.
    {: .revision-update }

The update is then shown in the note instead of the revision description. The
note is added at the end of the block, so that readers that ignore the styles,
like feed readers, show the update right after the original text.
"""

import datetime
import logging
import re

from bs4 import BeautifulSoup
from markdown import Markdown
from pelican import contents
from pelican import signals
from pelican.utils import set_date_tzinfo

logger = logging.getLogger(__name__)

_REVISION = re.compile(r"^(\d{4}-\d{2}-\d{2})\s*:\s*(.+)$")


class Revision:
    def __init__(self, date, locale_date, html):
        self.date = date
        self.locale_date = locale_date
        self.html = html


def _render_inline(md, text):
    """Render a line of Markdown without the enclosing paragraph."""
    md.reset()
    html = md.convert(text).strip()
    if html.startswith("<p>") and html.endswith("</p>"):
        html = html[3:-4]
    return html


def _annotate(content, log):
    """Add a margin note to every block marked with a revision date."""
    if not content._content or "data-revision" not in content._content:
        return

    by_day = {r.date.date().isoformat(): r for r in log}
    soup = BeautifulSoup(content._content, "html.parser")

    for block in soup.find_all(attrs={"data-revision": True}):
        day = block["data-revision"]
        revision = by_day.get(day)
        if revision is None:
            logger.warning(
                "No revision dated %s in %s for a block marked with it",
                day,
                content.source_path,
            )
            continue

        update = block.find_next_sibling()
        if update is not None and "revision-update" in update.get("class", []):
            text = update.decode_contents().strip()
            update.decompose()
        else:
            text = revision.html

        block["class"] = block.get("class", []) + ["revised"]
        note = BeautifulSoup(
            f'<span class="revision-note" tabindex="0" role="note" '
            f'aria-label="Updated on {day}"> <span class="revision-mark">~</span>'
            f'<span class="revision-popup"><time datetime="{day}">Update {day}</time> '
            f'{text} <a href="#revisions">Revision log</a></span></span>',
            "html.parser",
        )
        block.append(note)

    content._content = soup.decode()


def revisions(content):
    if isinstance(content, contents.Static):
        return

    raw = content.metadata.get("revisions")
    if not raw:
        content.revisions = []
        return

    lines = [raw] if isinstance(raw, str) else raw
    # Not the site-wide MARKDOWN settings: they include the meta extension,
    # which would swallow any description that starts with "Word: ...".
    md = Markdown(extensions=["markdown.extensions.extra"], output_format="html5")
    tz = content.settings.get("TIMEZONE")

    log = []
    for line in lines:
        match = _REVISION.match(line.strip())
        if match is None:
            logger.warning(
                "Ignoring malformed revision %r in %s (expected 'YYYY-MM-DD: text')",
                line,
                content.source_path,
            )
            continue
        day, text = match.groups()
        date = set_date_tzinfo(
            datetime.datetime.combine(datetime.date.fromisoformat(day), datetime.time()), tz
        )
        log.append(
            Revision(date, date.strftime(content.date_format), _render_inline(md, text))
        )

    log.sort(key=lambda r: r.date, reverse=True)
    content.revisions = log
    _annotate(content, log)

    if log and "modified" not in content.metadata:
        content.modified = log[0].date
        content.locale_modified = log[0].locale_date


def register():
    signals.content_object_init.connect(revisions)
