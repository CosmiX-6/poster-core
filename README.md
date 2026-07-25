# poster-core

AI-powered Visual News Intelligence engine. Give it an article URL, an RSS/newsroom
feed, a press release, or any custom text/structured input, and it produces
publication-ready social visuals: cover images, explanatory carousels,
infographics, and thumbnails.

It works like an automated editorial desk:

1. **Ingest** — URL, RSS/Atom feed, raw text, dict, or an `Article` you build yourself.
2. **Understand** — an LLM produces an editorial brief: key event, entities, facts,
   timeline, story beats, tone, and visual concepts (never inventing facts).
3. **Direct** — deterministic creative direction picks the most effective format(s)
   and turns the brief into concrete asset plans.
4. **Source images** — the article's own photography first, then stock
   (Unsplash/Pexels), then AI generation (OpenAI `gpt-image-1` or Google Imagen) —
   the order is a configurable policy.
5. **Render** — Pillow composes platform-sized PNGs with your brand kit, with
   image credits preserved.

## Install

```bash
pip install -e ".[all]"        # or pick extras: [openai] [gemini] [extraction]
```

API keys via standard env vars: `OPENAI_API_KEY`, `GOOGLE_API_KEY`,
`UNSPLASH_ACCESS_KEY`, `PEXELS_API_KEY`. Only the providers you use need keys.

## Use as a library

```python
from poster_core import Pipeline, PipelineConfig, BrandKit, AssetType, Platform

pipe = Pipeline(PipelineConfig(
    text_provider="openai",          # or "gemini"
    image_provider="gemini",         # or "openai" / "none"
    brand=BrandKit(name="My Brand", accent_color="#E4572E", footer="mybrand.com"),
))

# Any input works: URL, raw text, dict, or Article
assets = pipe.run("https://example.com/some-article")
assets = pipe.run("Headline\nBody text...", asset_types=[AssetType.COVER],
                  platform=Platform.LINKEDIN)

for asset in assets:
    print(asset.asset_type, asset.paths, asset.credit)

# Newsroom / press-portal feeds
from poster_core import load_feed
for article in load_feed("https://newsroom.example.com/rss", limit=5):
    pipe.run(article)

# Analysis only (no rendering) — useful inside other products
article, brief = pipe.analyze("https://example.com/some-article")
```

Every stage is pluggable: pass your own `llm` (anything with
`complete_json(system, user) -> dict`), `generator`
(`generate(prompt, size) -> bytes`), or `stock` provider to `Pipeline(...)`.

## CLI

```bash
poster https://example.com/article --types cover carousel --platform instagram_post
poster press-release.txt --image-provider gemini --accent "#0055FF" --footer "acme.com"
cat article.txt | poster - --types infographic
```

## Development

```bash
pip install -e . pytest
pytest
```

Tests run fully offline against fake providers — no API keys needed.
