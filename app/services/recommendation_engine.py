"""Orchestrator service for restaurant recommendations."""

import json
import logging
from app.data.repository import RestaurantRepository
from app.llm.client import LLMClient
from app.llm.parser import ResponseParser
from app.llm.prompts import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE
from app.models.preferences import UserPreferences
from app.models.recommendation import RecommendationMetadata, RecommendationResponse
from app.models.restaurant import Restaurant
from app.services.fallback_ranker import FallbackRanker

logger = logging.getLogger(__name__)


class RecommendationEngine:
    """Orchestrates candidate filtering, prompting, LLM query, parsing, and fallback ranking."""

    def __init__(self, repository: RestaurantRepository):
        self.repository = repository
        self.llm_client = LLMClient()
        self.parser = ResponseParser()
        self.fallback_ranker = FallbackRanker()

    def recommend(
        self,
        prefs: UserPreferences,
        candidates: list[Restaurant],
        context: dict,
    ) -> RecommendationResponse:
        """Query the LLM to get ranked recommendations, falling back to heuristics on failure.

        Args:
            prefs: Cleaned UserPreferences.
            candidates: Selected Restaurant candidates.
            context: Context built from FilterService.

        Returns:
            RecommendationResponse containing Ranked Recommendations and metadata.
        """
        logger.info(f"Generating recommendations for {len(candidates)} candidates.")

        # Serialize candidates for user prompt
        candidates_json = json.dumps(context["candidates"], indent=2)

        # Render user prompt
        user_prompt = USER_PROMPT_TEMPLATE.format(
            location=context["preferences"]["location"],
            budget=context["preferences"]["budget"],
            cuisine=context["preferences"]["cuisine"],
            min_rating=context["preferences"]["min_rating"],
            additional_preferences=context["preferences"]["additional_preferences"] or "None",
            candidates_json=candidates_json,
        )

        metadata_dict = context.get("metadata", {})

        # Attempt Groq API Completion with Retry-Once logic on JSON parse failure
        system_prompt = SYSTEM_PROMPT
        attempts = 2
        last_exception = None

        for attempt in range(1, attempts + 1):
            try:
                # 1. Query Groq API
                raw_response = self.llm_client.get_recommendations(system_prompt, user_prompt)
                
                # 2. Parse and Validate LLM Response
                response = self.parser.parse(raw_response, candidates)

                if not response.recommendations:
                    msg = "LLM returned zero valid recommendations."
                    raise ValueError(msg)

                # 3. Add metadata and return success
                response.metadata = RecommendationMetadata(
                    candidates_considered=metadata_dict.get("candidates_considered", len(candidates)),
                    filters_applied=metadata_dict.get("filters_applied", []),
                    filters_relaxed=metadata_dict.get("filters_relaxed", []),
                    used_fallback=False,
                )
                logger.info("Recommendation successfully generated via Groq LLM.")
                return response

            except Exception as e:
                last_exception = e
                logger.warning(
                    f"LLM attempt {attempt} failed: {e}. "
                    f"{'Retrying with stricter prompt' if attempt < attempts else 'Falling back to rule-based ranking'}"
                )
                
                # Append strict instructions on first failure to help retry
                system_prompt = (
                    SYSTEM_PROMPT
                    + "\n\nIMPORTANT: Your previous response was invalid, incomplete, or failed JSON/schema validation. "
                    "Make absolutely sure to return ONLY a single, valid JSON object containing exactly the 'summary' and "
                    "'recommendations' keys. Ensure all fields are populated and IDs correspond to the candidate list."
                )

        # 4. Fallback execution on all failed attempts
        logger.error(f"All LLM attempts failed. Falling back. Last error: {last_exception}")
        return self.fallback_ranker.rank(prefs, candidates, metadata=metadata_dict)
