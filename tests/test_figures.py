from types import SimpleNamespace

from bs4 import BeautifulSoup

import figures


def render(html):
    content = SimpleNamespace(_content=html)
    figures.figures(content)
    return BeautifulSoup(content._content, "html.parser")


def test_captioned_image_becomes_figure():
    soup = render(
        '<p><img alt="x" class="center-image" src="a.png">\n<em>A <code>caption</code></em></p>'
    )

    figure = soup.find("figure")
    assert figure is not None
    assert soup.find("p") is None
    assert figure.a["href"] == "a.png"
    assert figure.a["target"] == "_blank"
    assert figure.a.img["src"] == "a.png"
    assert figure.figcaption.decode_contents() == "A <code>caption</code>"


def test_image_without_caption_is_only_linked():
    soup = render('<p><img alt="x" src="a.png"></p>')

    assert soup.find("figure") is None
    assert soup.p.a["href"] == "a.png"
    assert soup.p.a.img["src"] == "a.png"


def test_image_in_running_text_is_not_a_figure():
    soup = render('<p>See <img src="a.png"> and <em>this</em>.</p>')

    assert soup.find("figure") is None
    assert soup.p.a.img["src"] == "a.png"


def test_linked_image_is_left_alone():
    soup = render('<p><a href="https://example.com"><img src="a.png"></a></p>')

    assert soup.find("figure") is None
    assert len(soup.find_all("a")) == 1
    assert soup.p.a["href"] == "https://example.com"


def test_code_caption_becomes_title():
    soup = render(
        '<div class="highlight"><pre><code>mov rax, 1</code></pre></div>\n'
        "<p><em>hello64.asm</em></p>"
    )

    figure = soup.find("figure", class_="code")
    assert figure is not None
    assert figure.figcaption.string == "hello64.asm"
    assert figure.find("div", class_="highlight") is not None
    assert soup.find("p") is None


def test_code_with_line_numbers_is_captioned_once():
    soup = render(
        '<div class="highlight"><table class="highlighttable"><tr>'
        '<td class="linenos"><div class="linenodiv"><pre>1</pre></div></td>'
        '<td class="code"><div><pre><code>x</code></pre></div></td>'
        "</tr></table></div>\n"
        "<p><em>hello64.asm</em></p>"
    )

    assert len(soup.find_all("figure")) == 1
    assert len(soup.find_all("figcaption")) == 1


def test_paragraph_after_code_is_kept():
    soup = render(
        '<div class="highlight"><pre><code>x</code></pre></div>\n'
        "<p><em>Note</em> that this is prose.</p>"
    )

    assert soup.find("figure") is None
    assert soup.p is not None
