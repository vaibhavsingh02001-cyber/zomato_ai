"""Controller for coordinating restaurant recommendation requests."""

import logging
from app.data.repository import RestaurantRepository
from app.services.preference_service import PreferenceService
from app.services.filter_service import FilterService
from app.services.recommendation_engine import RecommendationEngine
from app.models.recommendation import RecommendationResponse

logger = logging.getLogger(__name__)


class RecommendationController:
    """Orchestrates validation, candidate selection, and LLM ranking for a request."""

    def __init__(self, repository: RestaurantRepository):
        self.repository = repository
        self.preference_service = PreferenceService(repository)
        self.filter_service = FilterService(repository)
        self.recommendation_engine = RecommendationEngine(repository)

    def get_recommendations(self, raw_prefs: dict) -> RecommendationResponse:
        """Orchestrates user inputs through validation, filtering, and the LLM engine.

        Args:
            raw_prefs: Raw user preference dictionary from the API.

        Returns:
            RecommendationResponse model containing summary, recommendations, and metadata.
        """
        logger.info("RecommendationController: processing incoming preferences.")
        
        # 1. Validate and normalize user input
        prefs = self.preference_service.validate(raw_prefs)
        
        # 2. Extract matching candidates and prepare prompt context
        candidates, context = self.filter_service.build_candidates(prefs)
        
        # 3. Call recommendation engine to get final list
        response = self.recommendation_engine.recommend(prefs, candidates, context)
        
        return response
