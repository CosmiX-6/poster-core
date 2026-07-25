"""poster-core: turn articles, feeds and custom content into social visuals."""

from .config import PipelineConfig
from .errors import (
    AnalysisError,
    ImageSourcingError,
    IngestError,
    PosterError,
    RenderError,
)
from .ingest import load_feed
from .models import (
    Article,
    AssetPlan,
    AssetType,
    BrandKit,
    ComparisonPair,
    ContentBrief,
    DeckSlide,
    GeneratedAsset,
    ImageOrigin,
    MoneyFlowStep,
    Platform,
    Quote,
    SlideKind,
    StoryCategory,
)
from .pipeline import Pipeline

__all__ = [
    "Pipeline",
    "PipelineConfig",
    "Article",
    "AssetPlan",
    "AssetType",
    "BrandKit",
    "ContentBrief",
    "GeneratedAsset",
    "ImageOrigin",
    "Platform",
    "load_feed",
    "PosterError",
    "IngestError",
    "AnalysisError",
    "ImageSourcingError",
    "RenderError",
]

__version__ = "0.1.0"
