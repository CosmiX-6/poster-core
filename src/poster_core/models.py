"""Core data models shared across the pipeline."""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field, field_validator


class AssetType(str, Enum):
    COVER = "cover"
    CAROUSEL = "carousel"
    INFOGRAPHIC = "infographic"
    THUMBNAIL = "thumbnail"


class Platform(str, Enum):
    INSTAGRAM_POST = "instagram_post"
    INSTAGRAM_STORY = "instagram_story"
    LINKEDIN = "linkedin"
    X = "x"
    YOUTUBE_THUMBNAIL = "youtube_thumbnail"


PLATFORM_SIZES: dict[Platform, tuple[int, int]] = {
    Platform.INSTAGRAM_POST: (1080, 1350),
    Platform.INSTAGRAM_STORY: (1080, 1920),
    Platform.LINKEDIN: (1200, 627),
    Platform.X: (1600, 900),
    Platform.YOUTUBE_THUMBNAIL: (1280, 720),
}


class ArticleImage(BaseModel):
    url: str
    caption: str | None = None


class Article(BaseModel):
    """Normalised input content, whatever the original source was."""

    title: str
    text: str
    url: str | None = None
    source_name: str | None = None
    published_at: datetime | None = None
    images: list[ArticleImage] = Field(default_factory=list)
    metadata: dict = Field(default_factory=dict)


class StoryCategory(str, Enum):
    BREAKING = "breaking"
    INVESTIGATION = "investigation"
    POLITICS = "politics"
    TECHNOLOGY = "technology"
    AI = "ai"
    FINANCE = "finance"
    BUSINESS = "business"
    SPORTS = "sports"
    SCIENCE = "science"
    HEALTH = "health"
    DISASTER = "disaster"
    PRODUCT_LAUNCH = "product_launch"
    GENERAL = "general"


class Quote(BaseModel):
    text: str
    attribution: str | None = None


class Entity(BaseModel):
    name: str
    kind: str = "other"  # person | organisation | place | product | other


class TimelineEvent(BaseModel):
    when: str
    what: str


class StoryBeat(BaseModel):
    """One step of the narrative, usable directly as a carousel slide."""

    heading: str
    body: str | None = None


class ContentBrief(BaseModel):
    """Editorial understanding of an article, produced by the analysis step."""

    key_event: str
    summary: str
    headline: str
    subheadline: str | None = None
    category: StoryCategory = StoryCategory.GENERAL
    entities: list[Entity] = Field(default_factory=list)
    key_facts: list[str] = Field(default_factory=list)
    timeline: list[TimelineEvent] = Field(default_factory=list)
    story_beats: list[StoryBeat] = Field(default_factory=list)
    notable_quote: Quote | None = None
    why_it_matters: str | None = None
    future_impact: str | None = None
    emotions: list[str] = Field(default_factory=list)
    tone: str = "neutral"
    visual_concepts: list[str] = Field(default_factory=list)
    image_search_query: str | None = None
    image_generation_prompt: str | None = None

    @field_validator("category", mode="before")
    @classmethod
    def _coerce_category(cls, v):
        try:
            return StoryCategory(str(v).strip().lower().replace(" ", "_"))
        except ValueError:
            return StoryCategory.GENERAL

    @field_validator("notable_quote", mode="before")
    @classmethod
    def _coerce_quote(cls, v):
        if isinstance(v, str):
            return Quote(text=v) if v.strip() else None
        return v


class SlideKind(str, Enum):
    HERO = "hero"
    TEXT = "text"
    TIMELINE = "timeline"
    STATS = "stats"
    QUOTE = "quote"


class DeckSlide(BaseModel):
    """One composed slide of a carousel narrative."""

    kind: SlideKind = SlideKind.TEXT
    kicker: str | None = None  # small accent label, e.g. "WHY IT MATTERS"
    heading: str | None = None
    body: str | None = None
    facts: list[str] = Field(default_factory=list)
    timeline: list[TimelineEvent] = Field(default_factory=list)
    quote: Quote | None = None


class AssetPlan(BaseModel):
    """Creative direction for one concrete asset."""

    asset_type: AssetType
    platform: Platform
    headline: str
    subheadline: str | None = None
    category: StoryCategory = StoryCategory.GENERAL
    slides: list[DeckSlide] = Field(default_factory=list)
    facts: list[str] = Field(default_factory=list)
    source_name: str | None = None
    reading_minutes: int | None = None
    image_search_query: str | None = None
    image_generation_prompt: str | None = None
    rationale: str | None = None
    custom_size: tuple[int, int] | None = None

    @property
    def size(self) -> tuple[int, int]:
        """Output dimensions: an explicit custom size wins over the platform preset."""
        return self.custom_size or PLATFORM_SIZES[self.platform]


class ImageOrigin(str, Enum):
    ARTICLE = "article"
    STOCK = "stock"
    GENERATED = "generated"
    NONE = "none"


class SourcedImage(BaseModel):
    origin: ImageOrigin
    data: bytes | None = None
    credit: str | None = None
    source_url: str | None = None


class BrandKit(BaseModel):
    name: str = ""
    accent_color: str = "#E4572E"
    background_color: str = "#12161C"
    text_color: str = "#FFFFFF"
    logo_path: str | None = None
    font_path: str | None = None
    footer: str | None = None


class GeneratedAsset(BaseModel):
    asset_type: AssetType
    platform: Platform
    paths: list[str]
    plan: AssetPlan
    image_origin: ImageOrigin = ImageOrigin.NONE
    credit: str | None = None
