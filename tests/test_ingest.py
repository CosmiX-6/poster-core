import pytest

from poster_core.errors import IngestError
from poster_core.ingest import load
from poster_core.ingest.url import article_from_html
from poster_core.models import Article


def test_load_passthrough_and_dict():
    article = Article(title="t", text="body")
    assert load(article) is article
    loaded = load({"title": "t", "text": "body"})
    assert loaded.title == "t"


def test_load_raw_text_uses_first_line_as_title():
    article = load("Big Headline\nThe body of the story goes here.")
    assert article.title == "Big Headline"
    assert article.text.startswith("The body")


def test_load_empty_raises():
    with pytest.raises(IngestError):
        load("   ")


def test_article_from_html_extracts_title_text_and_og_image(monkeypatch):
    # Force the bs4 fallback path so the test behaves the same whether or
    # not trafilatura is installed.
    import poster_core.ingest.url as url_mod

    monkeypatch.setattr(url_mod, "_extract_with_trafilatura", lambda html: None)
    html = """
    <html><head>
      <title>Fallback</title>
      <meta property="og:title" content="Real Title">
      <meta property="og:image" content="/img/hero.jpg">
      <meta property="og:site_name" content="Example News">
    </head><body>
      <p>This is the first paragraph of the article and it is long enough to count.</p>
      <p>short</p>
      <p>This is the second paragraph of the article, also long enough to be kept.</p>
    </body></html>
    """
    article = article_from_html(html, url="https://news.example.com/story")
    assert article.title == "Real Title"
    assert article.source_name == "Example News"
    assert "first paragraph" in article.text
    assert "short" not in article.text
    assert article.images[0].url == "https://news.example.com/img/hero.jpg"
