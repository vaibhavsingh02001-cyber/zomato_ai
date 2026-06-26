"""Restaurant domain model."""

from pydantic import BaseModel, Field

from app.models.preferences import BudgetTier


class Restaurant(BaseModel):
    """A restaurant record from the Zomato dataset."""

    id: str
    name: str
    location: str
    cuisine: list[str]
    rating: float = Field(ge=0.0, le=5.0)
    estimated_cost: str
    budget_tier: BudgetTier
