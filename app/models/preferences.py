"""User preference models."""

from enum import Enum

from pydantic import BaseModel, Field, field_validator


class BudgetTier(str, Enum):
    """Budget tier for filtering and display."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class UserPreferences(BaseModel):
    """Validated user inputs for restaurant recommendations."""

    location: str
    budget: BudgetTier
    cuisine: str
    min_rating: float = Field(default=0.0, ge=0.0, le=5.0)
    additional_preferences: str | None = None

    @field_validator("location", "cuisine")
    @classmethod
    def strip_and_require_non_empty(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            msg = "must not be empty"
            raise ValueError(msg)
        return stripped

    @field_validator("additional_preferences")
    @classmethod
    def strip_optional_preferences(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None
