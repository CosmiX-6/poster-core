"""Command-line interface: `poster <source> [options]`."""

from __future__ import annotations

import argparse
import sys

from .config import PipelineConfig
from .errors import PosterError
from .models import AssetType, BrandKit, ImageOrigin, Platform
from .pipeline import Pipeline


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="poster",
        description="Turn an article URL, RSS feed or text file into social visuals.",
    )
    parser.add_argument("source", help="Article URL, path to a text file, or '-' for stdin")
    parser.add_argument(
        "--types",
        nargs="+",
        choices=[t.value for t in AssetType],
        help="Asset types to produce (default: chosen automatically)",
    )
    parser.add_argument(
        "--platform",
        choices=[p.value for p in Platform],
        default=Platform.INSTAGRAM_POST.value,
    )
    parser.add_argument("--out", default="output", help="Output directory")
    parser.add_argument(
        "--text-provider", choices=["openai", "gemini"], default="openai"
    )
    parser.add_argument(
        "--image-provider", choices=["openai", "gemini", "none"], default="openai"
    )
    parser.add_argument(
        "--no-stock", action="store_true", help="Skip stock photo search"
    )
    parser.add_argument("--accent", default=None, help="Brand accent colour, e.g. #E4572E")
    parser.add_argument("--footer", default=None, help="Footer/brand line on assets")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    source: str = args.source
    if source == "-":
        source = sys.stdin.read()
    elif not source.startswith(("http://", "https://")):
        try:
            with open(source, encoding="utf-8") as fh:
                source = fh.read()
        except OSError:
            pass  # treat as raw text

    policy = [ImageOrigin.ARTICLE, ImageOrigin.STOCK, ImageOrigin.GENERATED]
    if args.no_stock:
        policy.remove(ImageOrigin.STOCK)

    brand = BrandKit()
    if args.accent:
        brand.accent_color = args.accent
    if args.footer:
        brand.footer = args.footer

    config = PipelineConfig(
        text_provider=args.text_provider,
        image_provider=args.image_provider,
        image_policy=policy,
        output_dir=args.out,
        brand=brand,
    )
    types = [AssetType(t) for t in args.types] if args.types else None

    try:
        assets = Pipeline(config).run(
            source, asset_types=types, platform=Platform(args.platform)
        )
    except PosterError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    for asset in assets:
        origin = f" [{asset.image_origin.value}]" if asset.image_origin else ""
        print(f"{asset.asset_type.value}{origin}:")
        for path in asset.paths:
            print(f"  {path}")
        if asset.credit:
            print(f"  credit: {asset.credit}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
