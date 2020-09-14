#!/usr/bin/env python
# -*- coding: utf-8 -*- #

import os
import os.path

AUTHOR = "Gabriele N. Tornetta"
SITENAME = "The Hub of Heliopolis"
SITEURL = "https://p403n1x87.github.io"
THEME = os.path.abspath("./theme")

PATH = "content"

TIMEZONE = "Europe/London"

DEFAULT_LANG = "en"

# Feed generation is usually not desired when developing
FEED_ALL_ATOM = "feeds/all.atom.xml"
CATEGORY_FEED_ATOM = None
TRANSLATION_FEED_ATOM = None
AUTHOR_FEED_ATOM = None
AUTHOR_FEED_RSS = None
DISPLAY_CATEGORIES_ON_MENU = False

# Blogroll
LINKS = (("RSS", FEED_ALL_ATOM),)

MENUITEMS = [("cd ~", "/")]

# Social widget
SOCIAL = [
    ("github", "https://github.com/p403n1x87"),
    ("linkedin", "https://www.linkedin.com/in/gabriele-tornetta-b2733759"),
    ("stack-exchange", "https://stackexchange.com/users/528399/phoenix87"),
    ("steam", "https://steamcommunity.com/profiles/76561198092800937"),
    ("twitter", "https://twitter.com/p403n1x87"),
    ("wikipedia-w", "https://en.wikipedia.org/wiki/User:Gabriele_Nunzio_Tornetta"),
]

DEFAULT_PAGINATION = 10

# Uncomment following line if you want document-relative URLs when developing
RELATIVE_URLS = True

# Plugins
PLUGIN_PATHS = ["./plugins"]
PLUGINS = ["render_math", "readtime"]

MARKDOWN = {
    "extension_configs": {
        "markdown.extensions.toc": {"title": "Table of contents:"},
        "markdown.extensions.codehilite": {"css_class": "highlight"},
        "markdown.extensions.extra": {},
        "markdown.extensions.meta": {},
    },
    "output_format": "html5",
}
