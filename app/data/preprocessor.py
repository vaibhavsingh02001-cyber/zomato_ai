"""Data preprocessor for Zomato restaurant records."""

import logging
import re
from app.models.preferences import BudgetTier
from app.models.restaurant import Restaurant

logger = logging.getLogger(__name__)


class Preprocessor:
    """Preprocesses raw Zomato dataset rows into validated Restaurant entities."""

    def __init__(self):
        # Location alias mapping (lowercase keys) for Delhi sub-areas
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

    def preprocess(self, raw_rows: list[dict]) -> list[Restaurant]:
        """Preprocesses list of raw rows into list of cleaned Restaurant objects."""
        logger.info(f"Starting preprocessing of {len(raw_rows)} raw rows.")

        processed_restaurants = {}
        dropped_missing_name = 0
        dropped_missing_location = 0
        dropped_missing_cuisine = 0
        dropped_invalid_rating = 0
        dropped_invalid_cost = 0
        deduplicated_count = 0

        for row in raw_rows:
            # 1. Extract raw values using multiple possible column keys
            raw_name = self._get_field(row, ["name", "Restaurant_Name", "Restaurant Name"])
            raw_location = self._get_field(row, ["location", "Place_Name", "Place Name", "city", "City", "listed_in(city)"])
            raw_cuisine = self._get_field(row, ["cuisines", "Cuisine", "cuisine"])
            raw_rating = self._get_field(row, ["rate", "rating", "Dining_Rating", "Dining_Rate", "Dining Rating"])
            raw_cost = self._get_field(
                row,
                [
                    "approx_cost(for two people)",
                    "cost",
                    "approx_cost",
                    "Cost",
                    "approx_cost_for_two",
                    "Average Cost for two",
                    "average_cost_for_two",
                ],
            )

            # 2. Validate/Clean Name
            if not raw_name or not str(raw_name).strip():
                dropped_missing_name += 1
                continue
            name = str(raw_name).strip()

            # 3. Validate/Clean Location
            if not raw_location or not str(raw_location).strip():
                dropped_missing_location += 1
                continue
            location_norm = str(raw_location).strip().lower()
            location = self.location_aliases.get(location_norm, location_norm)

            # 4. Validate/Clean Cuisine
            if not raw_cuisine or not str(raw_cuisine).strip():
                dropped_missing_cuisine += 1
                continue
            cuisine_str = str(raw_cuisine)
            # Split by comma, strip whitespace, lowercase, filter empty, and deduplicate
            cuisines = sorted(list(set(
                c.strip().lower() for c in cuisine_str.split(",") if c.strip()
            )))
            if not cuisines:
                dropped_missing_cuisine += 1
                continue

            # 5. Validate/Clean Rating
            rating = self._parse_rating(raw_rating)
            if rating is None:
                dropped_invalid_rating += 1
                continue

            # 6. Validate/Clean Cost & Budget Tier
            cost_info = self._parse_cost_and_tier(raw_cost)
            if cost_info is None:
                dropped_invalid_cost += 1
                continue
            estimated_cost, budget_tier = cost_info

            # Create a candidate dictionary for the Restaurant model
            # Note: id will be assigned after deduplication to ensure stable sequential IDs
            restaurant_dict = {
                "name": name,
                "location": location,
                "cuisine": cuisines,
                "rating": rating,
                "estimated_cost": estimated_cost,
                "budget_tier": budget_tier,
            }

            # 7. Deduplicate by name + location (case-insensitive name check)
            dedup_key = (name.lower(), location)
            if dedup_key in processed_restaurants:
                # Keep the one with the higher rating
                existing_restaurant = processed_restaurants[dedup_key]
                if rating > existing_restaurant["rating"]:
                    processed_restaurants[dedup_key] = restaurant_dict
                deduplicated_count += 1
            else:
                processed_restaurants[dedup_key] = restaurant_dict

        # Assign stable sequential IDs to the final list of deduplicated restaurants
        final_restaurants = []
        for i, item in enumerate(processed_restaurants.values(), 1):
            restaurant_id = f"r_{i:04d}"
            item["id"] = restaurant_id
            final_restaurants.append(Restaurant.model_validate(item))

        logger.info(
            f"Preprocessing complete. Final count: {len(final_restaurants)}. "
            f"Dropped missing name: {dropped_missing_name}, "
            f"Dropped missing location: {dropped_missing_location}, "
            f"Dropped missing cuisine: {dropped_missing_cuisine}, "
            f"Dropped invalid rating: {dropped_invalid_rating}, "
            f"Dropped invalid cost: {dropped_invalid_cost}, "
            f"Deduplicated rows: {deduplicated_count}."
        )

        return final_restaurants

    def _get_field(self, row: dict, keys: list[str]) -> any:
        """Helper to try multiple column keys on a dictionary."""
        for key in keys:
            if key in row and row[key] is not None:
                return row[key]
        return None

    def _parse_rating(self, raw_rating: any) -> float | None:
        """Parses rating value into float. Clamps 0-5. Returns None if invalid."""
        if raw_rating is None:
            return None
        
        rating_str = str(raw_rating).strip()
        if not rating_str or rating_str in ["-", "NEW", "None"]:
            return None

        # Handle '4.1/5' format
        if "/" in rating_str:
            rating_str = rating_str.split("/")[0].strip()

        try:
            val = float(rating_str)
            if 0.0 <= val <= 5.0:
                return val
            # Clamp to 0-5 if slightly out of range, or return None if wildly invalid
            if val < 0.0:
                return 0.0
            if val > 5.0:
                return 5.0
        except ValueError:
            return None
        return None

    def _parse_cost_and_tier(self, raw_cost: any) -> tuple[str, BudgetTier] | None:
        """Parses cost and maps to a budget tier. Returns None if invalid."""
        if raw_cost is None:
            return None

        cost_str = str(raw_cost).strip()
        if not cost_str or cost_str in ["-", "None", "N/A", "--"]:
            return None

        # Clean string from currency signs and commas
        cleaned_cost = cost_str.replace("₹", "").replace(",", "").strip()

        # Find first number sequence in string
        match = re.search(r"\d+", cleaned_cost)
        if not match:
            return None

        try:
            cost_val = int(match.group())
        except ValueError:
            return None

        # Fixed threshold budget tier mapping:
        # low <= 400
        # medium: 401 to 1000
        # high > 1000
        if cost_val <= 400:
            tier = BudgetTier.LOW
        elif cost_val <= 1000:
            tier = BudgetTier.MEDIUM
        else:
            tier = BudgetTier.HIGH

        # Format estimated cost nicely
        formatted_cost = f"₹{cost_val} for two"
        return formatted_cost, tier
