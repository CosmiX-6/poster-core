"""Exception hierarchy for poster-core."""


class PosterError(Exception):
    """Base class for all poster-core errors."""


class IngestError(PosterError):
    """Failed to load or parse source content."""


class AnalysisError(PosterError):
    """LLM analysis failed or returned unusable output."""


class ImageSourcingError(PosterError):
    """No usable image could be sourced for a plan."""


class RenderError(PosterError):
    """Failed to compose the final asset."""
