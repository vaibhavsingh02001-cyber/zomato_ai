"""Fallback rule-based ranking engine for when the LLM is unavailable."""

import logging
from app.config import settings
from app.models.preferences import UserPreferences
from app.models.recommendation import (
    Recommendation,
    RecommendationMetadata,
    RecommendationResponse,
)
from app.models.restaurant import Restaurant

logger = logging.getLogger(__name__)


class FallbackRanker:
    """Ranks candidates using structured heuristics and templates instead of an LLM."""

    def rank(
        self,
        prefs: UserPreferences,
        candidates: list[Restaurant],
        metadata: dict | None = None,
    ) -> RecommendationResponse:
        """Sorts candidates by rating, maps to recommendations with template explanations.

        Fills up to settings.top_recommendations.
        """
        logger.info(
            f"Invoking fallback ranking for {len(candidates)} candidates. "
            f"Prefs: {prefs}"
        )

        # 1. Primary sort: rating desc, secondary sort: id asc for stable tie-breaker
        sorted_candidates = sorted(candidates, key=lambda r: (-r.rating, r.id))

        # 2. Select top N recommendations
        top_n = settings.top_recommendations
        selected_candidates = sorted_candidates[:top_n]

        recommendations = []
        for idx, r in enumerate(selected_candidates, 1):
            cuisine_str = ", ".join(r.cuisine)
            
            # Generate natural explanation from template
            explanation = (
                f"Rated {r.rating} with {cuisine_str} cuisine in {r.location}. "
                f"It matches your {prefs.budget.value} budget preference with an "
                f"estimated cost of {r.estimated_cost}."
            )

            rec = Recommendation(
                rank=idx,
                restaurant_id=r.id,
                name=r.name,
                cuisine=cuisine_str,
                rating=r.rating,
                estimated_cost=r.estimated_cost,
                explanation=explanation,
            )
            recommendations.append(rec)

        summary = (
            "Note: The AI recommendation service is temporarily unavailable. "
            "We have fallen back to a rule-based ranking to suggest the highest-rated "
            "restaurants matching your preferences."
        )

        # 3. Assemble response metadata
        meta_dict = metadata or {}
        response_metadata = RecommendationMetadata(
            candidates_considered=meta_dict.get("candidates_considered", len(candidates)),
            filters_applied=meta_dict.get("filters_applied", []),
            filters_relaxed=meta_dict.get("filters_relaxed", []),
            used_fallback=True,
        )

        return RecommendationResponse(
            summary=summary,
            recommendations=recommendations,
            metadata=response_metadata,
        )
