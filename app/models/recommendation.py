"""Recommendation response models."""

from pydantic import BaseModel, Field


class Recommendation(BaseModel):
    """A single ranked restaurant recommendation."""

    rank: int = Field(ge=1)
    restaurant_id: str
    name: str
    cuisine: str
    rating: float = Field(ge=0.0, le=5.0)
    estimated_cost: str
    explanation: str


class RecommendationMetadata(BaseModel):
    """Optional metadata about how recommendations were produced."""

    candidates_considered: int | None = None
    filters_applied: list[str] = Field(default_factory=list)
    filters_relaxed: list[str] | None = None
    used_fallback: bool = False


class RecommendationResponse(BaseModel):
    """Full API response for a recommendation request."""

    summary: str | None = None
    recommendations: list[Recommendation]
    metadata: RecommendationMetadata | dict = Field(default_factory=dict)
