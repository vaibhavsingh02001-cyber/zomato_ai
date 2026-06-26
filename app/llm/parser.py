"""Parser for validating and cleaning Groq LLM JSON responses."""

import json
import logging
import re
from app.models.recommendation import Recommendation, RecommendationResponse
from app.models.restaurant import Restaurant

logger = logging.getLogger(__name__)


class ResponseParser:
    """Parses text responses from Groq into validated RecommendationResponse objects."""

    def parse(self, text: str, candidate_pool: list[Restaurant]) -> RecommendationResponse:
        """Parses raw text response from LLM, validates, and cleans the output.

        Normalizes structured fields with dataset source-of-truth values and filters
        out hallucinated restaurant IDs.
        """
        cleaned = text.strip()
        
        # 1. Strip markdown fences if present
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
            cleaned = re.sub(r"\s*```$", "", cleaned)
            cleaned = cleaned.strip()

        # 2. Parse JSON string
        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError as e:
            msg = f"Failed to parse LLM output as JSON: {e}"
            logger.error(msg)
            raise ValueError(msg) from e

        # 3. Validate against Pydantic model
        try:
            response = RecommendationResponse.model_validate(data)
        except Exception as e:
            msg = f"LLM JSON schema mismatch: {e}"
            logger.error(msg)
            raise ValueError(msg) from e

        # 4. Validate IDs and overwrite structured fields with source of truth (dataset)
        candidate_map = {c.id: c for c in candidate_pool}
        valid_recommendations = []

        for rec in response.recommendations:
            if rec.restaurant_id in candidate_map:
                candidate = candidate_map[rec.restaurant_id]
                
                # Overwrite fields with source-of-truth values to guard against LLM hallucination
                rec.name = candidate.name
                rec.cuisine = ", ".join(candidate.cuisine)
                rec.rating = candidate.rating
                rec.estimated_cost = candidate.estimated_cost
                
                valid_recommendations.append(rec)
            else:
                logger.warning(
                    f"Dropped hallucinated restaurant ID: '{rec.restaurant_id}' "
                    f"(Name claimed: '{rec.name}')"
                )

        # 5. Re-rank sequentially to fix any gaps/duplicates in LLM ranks
        for idx, rec in enumerate(valid_recommendations, 1):
            rec.rank = idx

        response.recommendations = valid_recommendations
        return response
