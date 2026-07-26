# poster-core

Turn any article, blog post, press release, or RSS feed into publication-ready
social visuals: a cover image, an infographic, or a documentary-style
swipeable carousel — designed automatically, per story, by an AI editorial
pipeline.

It works like an automated editorial desk, not a template filler:

1. **Ingest** — a URL, an RSS/Atom feed, raw text, a dict, or an `Article` you
   build yourself.
2. **Understand** — one LLM call reads the article like an editor and
   produces a structured brief: headline, story category, key facts,
   timeline, a notable quote, a money trail if one exists, a before/after
   comparison if one exists — all grounded in the article, never invented.
3. **Direct** — deterministic logic (no LLM, so it's free and instant) turns
   the brief into a concrete plan: which asset types to produce, and for a
   carousel, which narrative chapters the story actually earns.
4. **Source an image** — the article's own photo first, then stock search
   (Unsplash/Pexels), then AI generation — in that order, configurable.
5. **Render** — Pillow composes the final PNGs using a semantic design
   system: each story category gets its own colour theme and icon set, and
   every layout block (stat cards, timelines, quote cards, money-flow
   diagrams, comparison cards) is sized to its actual content.

## Install

```bash
pip install -e ".[all]"        # everything
# or pick only what you need:
pip install -e ".[openai]"     # OpenAI text + image generation
pip install -e ".[gemini]"     # Gemini text + Imagen generation
pip install -e ".[extraction]" # better article-body extraction (trafilatura)
```

Requires Python 3.10+.

## Get API keys

Copy the template and fill in what you have — only the providers you
actually use need a key:

```bash
cp .env.example .env
```

| Variable | What it's for | Where to get it |
|---|---|---|
| `OPENAI_API_KEY` | Text analysis (default) and `gpt-image-1` generation | platform.openai.com |
| `GOOGLE_API_KEY` | Gemini text analysis and Imagen generation (`--text-provider gemini`) | aistudio.google.com/apikey |
| `UNSPLASH_ACCESS_KEY` | Real stock photos (optional) | unsplash.com/developers |
| `PEXELS_API_KEY` | Real stock photos, second source (optional) | pexels.com/api |

Without stock keys, the pipeline just skips straight to AI image generation.
Without any image provider, covers and carousel hero slides fall back to a
clean typographic treatment (no image, still fully designed).

Load the file before running anything:

```bash
set -a; source .env; set +a
```

## Quick start (CLI)

```bash
# A live article → an auto-chosen set of assets in ./output/<slug>/
poster https://example.com/some-article

# Just a cover, for a specific platform
poster https://example.com/some-article --types cover --platform linkedin

# The full documentary carousel
poster https://example.com/some-article --types carousel

# Your own text, no image generation (still needs a text-provider key for analysis)
printf "Headline\nBody text of the piece..." | poster - --types infographic --image-provider none

# Gemini instead of OpenAI, custom brand
poster https://example.com/article \
  --text-provider gemini --image-provider gemini \
  --accent "#0055FF" --brand-name "Daily Wire" --footer "dailywire.example"
```

Run `poster --help` for the full flag reference. Every run prints the output
paths, the image origin (`article` / `stock` / `generated` / `none`), and the
photo credit when there is one.

### All CLI flags

| Flag | Default | What it does |
|---|---|---|
| `source` | — | URL, path to a text file, or `-` for stdin |
| `--types` | auto-selected | one or more of `cover carousel infographic thumbnail` |
| `--platform` | `instagram_post` | `instagram_post` `instagram_story` `linkedin` `x` `youtube_thumbnail` |
| `--out` | `output` | output directory |
| `--text-provider` | `openai` | `openai` or `gemini` |
| `--image-provider` | `openai` | `openai`, `gemini`, or `none` |
| `--no-stock` | off | skip Unsplash/Pexels, go straight to AI generation |
| `--size` | platform preset | custom `WxH`, e.g. `1080x1080` |
| `--accent` | `#E4572E` | brand accent colour (overrides the category's semantic colour) |
| `--brand-name` | — | channel/brand name shown on assets |
| `--footer` | — | footer line on assets (e.g. your domain) |

## Use as a library

This is the primary way to use poster-core — embedded in another project,
with full control over providers, sizing, and branding per call.

```python
from poster_core import Pipeline, PipelineConfig, BrandKit, AssetType, Platform

pipe = Pipeline(PipelineConfig(
    text_provider="openai",          # or "gemini"
    image_provider="gemini",         # or "openai" / "none"
    brand=BrandKit(name="My Brand", accent_color="#E4572E", footer="mybrand.com"),
))

# Any input works: URL, raw text, dict, or a prebuilt Article
assets = pipe.run("https://example.com/some-article")
assets = pipe.run(
    "Headline\nBody text...",
    asset_types=[AssetType.COVER],
    platform=Platform.LINKEDIN,
    size=(1080, 1080),                       # per-run size override
    brand=BrandKit(footer="othersite.com"),  # per-run brand override
)

for asset in assets:
    print(asset.asset_type, asset.paths, asset.image_origin, asset.credit)

# Newsroom / press-portal RSS feeds
from poster_core import load_feed
for article in load_feed("https://newsroom.example.com/rss", limit=5):
    pipe.run(article)

# Editorial analysis only, no rendering — useful for previewing or for
# feeding the brief into your own UI before committing to an image
article, brief = pipe.analyze("https://example.com/some-article")
print(brief.headline, brief.category, brief.hook)
```

Every stage is pluggable. Pass your own implementation to `Pipeline(...)`:

- `llm`: anything with `complete_json(system, user) -> dict`
- `generator`: anything with `generate(prompt, size) -> bytes`
- `stock`: anything with `search(query, size) -> SourcedImage | None`

See `analysis/llm.py` and `images/base.py` for the exact protocols.

## Asset types

| Type | What it is |
|---|---|
| `cover` | One full-bleed hero image with headline, subheadline, category chip and credit — a single shareable image |
| `carousel` | A documentary-style multi-slide narrative (see below) — up to 10 slides sized for Instagram/Threads |
| `infographic` | One image: headline plus up to five key-fact stat cards |
| `thumbnail` | A cover variant with larger, shorter text, for YouTube-style thumbnails |

If you don't pass `asset_types`, the pipeline picks automatically: a cover is
always produced; a carousel is added when the story has enough narrative
material (3+ story beats or timeline events); an infographic is added when
there are 3+ numeric facts.

## The carousel: how the narrative is built

The carousel isn't a fixed template — it's composed per story from whichever
of these chapters the article actually supports (nothing is invented to pad
it out):

```
HOOK → WHAT HAPPENED → THE DETAIL → WHY IT MATTERS → FOLLOW THE MONEY
     → HOW IT UNFOLDED → KEY NUMBERS → BEFORE/AFTER → QUOTE → WHAT'S NEXT
```

- **Hook** — a curiosity-first opening line, written to be distinct from the
  headline, over a heavily darkened hero image ("Swipe to uncover the
  story").
- **What happened / The detail / Why it matters** — alternate automatically
  between a plain text layout and a case-file "evidence card" layout, so two
  prose slides never look identical back to back.
- **Follow the money** — only appears if the article describes a real money
  trail (donations, transfers, funding); renders as a vertical flow diagram
  of boxed actors linked by amount-labelled arrows.
- **How it unfolded** — only appears with 3+ dated events; a vertical
  timeline.
- **Key numbers** — only appears with 2+ numeric facts; oversized-figure stat
  cards.
- **Before/After** — only appears if the article supports a clear two-way
  comparison; a split card with a "VS" badge.
- **Quote** — only appears if a striking quote was actually in the article.
- **What's next** — the deliberate close: reuses the hook's cinematic
  backdrop to bookend the story, built from a forward-looking closing line.

Every slide but the last ends with a short swipe-bait transition line
("But that wasn't where the story began. →").

## Story categories and colour

The brief classifies every story into one of 13 categories — `breaking`,
`investigation`, `politics`, `technology`, `ai`, `finance`, `business`,
`sports`, `science`, `health`, `disaster`, `product_launch`, `general` — and
each resolves to its own accent colour, background, and icon set (e.g. red
for politics/breaking, green for finance, purple for AI/science). Passing a
custom `accent_color` in your `BrandKit` overrides the category colour while
keeping everything else themed correctly.

## Development

```bash
pip install -e . pytest
pytest
```

The full test suite runs offline against fake LLM/image/stock providers —
no API keys needed, no network calls.
