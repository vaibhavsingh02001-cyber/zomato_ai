"""Service for filtering restaurants based on user preferences."""

import logging
from app.config import settings
from app.data.repository import RestaurantRepository
from app.models.preferences import UserPreferences
from app.models.restaurant import Restaurant
from app.services.context_builder import PromptContextBuilder

logger = logging.getLogger(__name__)


class FilterService:
    """Handles logic for narrowing down the restaurant list to a candidate pool."""

    def __init__(self, repository: RestaurantRepository):
        self.repository = repository
        self.context_builder = PromptContextBuilder()

    def build_candidates(self, prefs: UserPreferences) -> tuple[list[Restaurant], dict]:
        """Filters, relaxes constraints if necessary, sorts, and builds prompt context.

        Returns:
            A tuple of (list of Restaurant candidates, prompt context dictionary).
        """
        logger.info(f"Filtering candidates for preferences: {prefs}")
        
        apply_cuisine = True
        apply_rating = True
        apply_budget = True

        filters_applied = ["location", "cuisine", "min_rating", "budget"]
        filters_relaxed = []

        # 1. Sequential filtering with progressive relaxation
        # Step 0: Strict filters
        candidates = self._apply_filters(
            prefs,
            apply_cuisine=apply_cuisine,
            apply_rating=apply_rating,
            apply_budget=apply_budget,
        )

        min_candidates = 3

        # Step 1: Relax cuisine
        if len(candidates) < min_candidates:
            logger.info(
                f"Strict filtering returned only {len(candidates)} candidates. "
                "Relaxing cuisine constraint."
            )
            apply_cuisine = False
            filters_applied.remove("cuisine")
            filters_relaxed.append("cuisine")
            candidates = self._apply_filters(
                prefs,
                apply_cuisine=apply_cuisine,
                apply_rating=apply_rating,
                apply_budget=apply_budget,
            )

        # Step 2: Relax min_rating
        if len(candidates) < min_candidates:
            logger.info(
                f"Filtering after relaxing cuisine returned {len(candidates)} candidates. "
                "Relaxing rating constraint."
            )
            apply_rating = False
            filters_applied.remove("min_rating")
            filters_relaxed.append("min_rating")
            candidates = self._apply_filters(
                prefs,
                apply_cuisine=apply_cuisine,
                apply_rating=apply_rating,
                apply_budget=apply_budget,
            )

        # Step 3: Relax budget
        if len(candidates) < min_candidates:
            logger.info(
                f"Filtering after relaxing rating returned {len(candidates)} candidates. "
                "Relaxing budget constraint."
            )
            apply_budget = False
            filters_applied.remove("budget")
            filters_relaxed.append("budget")
            candidates = self._apply_filters(
                prefs,
                apply_cuisine=apply_cuisine,
                apply_rating=apply_rating,
                apply_budget=apply_budget,
            )

        # 2. Check if still completely empty
        if not candidates:
            logger.warning("No restaurants found even after full filter relaxation.")
            msg = "No restaurants match your criteria even after filter relaxation."
            raise LookupError(msg)

        # 3. Sort candidates by rating descending (stable sort, tie-broken by ID)
        candidates.sort(key=lambda r: (-r.rating, r.id))

        # 4. Limit to MAX_CANDIDATES
        max_cands = settings.max_candidates
        selected_candidates = candidates[:max_cands]
        logger.info(
            f"Selected {len(selected_candidates)} candidates for the LLM. "
            f"Applied: {filters_applied}, Relaxed: {filters_relaxed}"
        )

        # 5. Build prompt context using context builder
        context = self.context_builder.build(
            prefs,
            selected_candidates,
            filters_applied=filters_applied,
            filters_relaxed=filters_relaxed,
        )

        return selected_candidates, context

    def _apply_filters(
        self,
        prefs: UserPreferences,
        apply_cuisine: bool,
        apply_rating: bool,
        apply_budget: bool,
    ) -> list[Restaurant]:
        """Applies enabled filter constraints to the repository data."""
        # Start with all restaurants at location
        candidates = self.repository.get_by_location(prefs.location)

        # Filter by cuisine (the restaurant cuisines list must contain user pref cuisine)
        if apply_cuisine and prefs.cuisine:
            candidates = [
                r for r in candidates
                if prefs.cuisine.lower() in [c.lower() for c in r.cuisine]
            ]

        # Filter by rating
        if apply_rating and prefs.min_rating > 0.0:
            candidates = [r for r in candidates if r.rating >= prefs.min_rating]

        # Filter by budget tier
        if apply_budget and prefs.budget:
            candidates = [r for r in candidates if r.budget_tier == prefs.budget]

        return candidates
