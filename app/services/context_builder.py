"""Service for building prompt context payloads for the LLM."""

from app.models.preferences import UserPreferences
from app.models.restaurant import Restaurant


class PromptContextBuilder:
    """Formats user preferences and filtered restaurant candidates into a structure for LLM prompts."""

    def build(
        self,
        prefs: UserPreferences,
        candidates: list[Restaurant],
        filters_applied: list[str],
        filters_relaxed: list[str],
    ) -> dict:
        """Serializes preferences and candidates to an LLM prompt-ready dictionary."""
        return {
            "preferences": {
                "location": prefs.location,
                "budget": prefs.budget.value,
                "cuisine": prefs.cuisine,
                "min_rating": prefs.min_rating,
                "additional_preferences": prefs.additional_preferences,
            },
            "candidates": [
                {
                    "id": r.id,
                    "name": r.name,
                    "location": r.location,
                    "cuisine": ", ".join(r.cuisine),
                    "rating": r.rating,
                    "estimated_cost": r.estimated_cost,
                    "budget_tier": r.budget_tier.value,
                }
                for r in candidates
            ],
            "metadata": {
                "candidates_considered": len(candidates),
                "filters_applied": filters_applied,
                "filters_relaxed": filters_relaxed,
            },
        }
