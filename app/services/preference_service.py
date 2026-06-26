"""Service for validating and normalizing user preferences."""

import difflib
import logging
import re
from app.data.repository import RestaurantRepository
from app.models.preferences import BudgetTier, UserPreferences

logger = logging.getLogger(__name__)


class PreferenceService:
    """Validates and normalizes raw user inputs into structured UserPreferences."""

    def __init__(self, repository: RestaurantRepository):
        self.repository = repository
        self.location_aliases = {
            "cp": "connaught place",
            "connaught pl": "connaught place",
            "hkv": "hauz khas",
            "hauz khas village": "hauz khas",
            "south ext": "south extension",
            "south extension i": "south extension",
            "south extension ii": "south extension",
            "dwarka sector 10": "dwarka",
            "dwarka sector 12": "dwarka",
        }

    def validate(self, raw_prefs: dict) -> UserPreferences:
        """Validates and normalizes raw user preferences input.

        Raises ValueError if any field fails validation.
        """
        logger.info(f"Validating user preferences: {raw_prefs}")

        # 1. Check for required keys
        if "location" not in raw_prefs or raw_prefs["location"] is None:
            msg = "location is required"
            raise ValueError(msg)
        if "budget" not in raw_prefs or raw_prefs["budget"] is None:
            msg = "budget is required"
            raise ValueError(msg)
        if "cuisine" not in raw_prefs or raw_prefs["cuisine"] is None:
            msg = "cuisine is required"
            raise ValueError(msg)

        location_input = str(raw_prefs["location"]).strip()
        budget_raw = raw_prefs["budget"]
        budget_str = budget_raw.value if hasattr(budget_raw, "value") else str(budget_raw)
        budget_input = budget_str.strip().lower()
        cuisine_input = str(raw_prefs["cuisine"]).strip()
        min_rating_input = raw_prefs.get("min_rating", 0.0)
        additional_prefs_input = raw_prefs.get("additional_preferences")

        # 2. Normalize and validate budget
        try:
            budget = BudgetTier(budget_input)
        except ValueError as e:
            msg = "budget must be one of: low, medium, high"
            raise ValueError(msg) from e

        # 3. Normalize and validate location
        loc_norm = location_input.lower()
        canonical_loc = self.location_aliases.get(loc_norm, loc_norm)
        known_locations = self.repository.get_known_locations()

        if canonical_loc not in known_locations:
            msg = (
                f"location '{location_input}' is not available. "
                f"Available locations: {', '.join(known_locations)}"
            )
            raise ValueError(msg)

        # 4. Fuzzy match cuisine
        cuisine_norm = cuisine_input.lower()
        known_cuisines = self.repository.get_known_cuisines()
        matched_cuisine = None

        if cuisine_norm in known_cuisines:
            matched_cuisine = cuisine_norm
        else:
            # Substring match
            sub_matches = [
                kc for kc in known_cuisines
                if cuisine_norm in kc or kc in cuisine_norm
            ]
            if sub_matches:
                matched_cuisine = sub_matches[0]
            else:
                # Fuzzy match
                close_matches = difflib.get_close_matches(
                    cuisine_norm, known_cuisines, n=1, cutoff=0.5
                )
                if close_matches:
                    matched_cuisine = close_matches[0]
                else:
                    msg = (
                        f"cuisine '{cuisine_input}' matches no known cuisines in the database."
                    )
                    raise ValueError(msg)

        # 5. Validate min rating
        try:
            min_rating = float(min_rating_input)
        except (ValueError, TypeError) as e:
            msg = "min_rating must be a number"
            raise ValueError(msg) from e

        if not (0.0 <= min_rating <= 5.0):
            msg = "min_rating must be between 0.0 and 5.0"
            raise ValueError(msg)

        # 6. Sanitize additional preferences (length cap and control char removal)
        sanitized_additional = None
        if additional_prefs_input is not None:
            # Strip control chars to prevent prompt injection
            clean_text = re.sub(
                r"[\x00-\x1F\x7F-\x9F]", "", str(additional_prefs_input)
            )
            # Truncate to 500 chars
            clean_text = clean_text[:500].strip()
            if clean_text:
                sanitized_additional = clean_text

        return UserPreferences(
            location=canonical_loc,
            budget=budget,
            cuisine=matched_cuisine,
            min_rating=min_rating,
            additional_preferences=sanitized_additional,
        )
