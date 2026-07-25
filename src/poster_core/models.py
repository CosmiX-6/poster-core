"""Core data models shared across the pipeline."""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


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
    entities: list[Entity] = Field(default_factory=list)
    key_facts: list[str] = Field(default_factory=list)
    timeline: list[TimelineEvent] = Field(default_factory=list)
    story_beats: list[StoryBeat] = Field(default_factory=list)
    emotions: list[str] = Field(default_factory=list)
    tone: str = "neutral"
    visual_concepts: list[str] = Field(default_factory=list)
    image_search_query: str | None = None
    image_generation_prompt: str | None = None


class AssetPlan(BaseModel):
    """Creative direction for one concrete asset."""

    asset_type: AssetType
    platform: Platform
    headline: str
    subheadline: str | None = None
    slides: list[StoryBeat] = Field(default_factory=list)
    facts: list[str] = Field(default_factory=list)
    image_search_query: str | None = None
    image_generation_prompt: str | None = None
    rationale: str | None = None

    @property
    def size(self) -> tuple[int, int]:
        return PLATFORM_SIZES[self.platform]


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
