"""In-memory repository for querying preprocessed restaurant data."""

import logging
from app.models.preferences import BudgetTier
from app.models.restaurant import Restaurant

logger = logging.getLogger(__name__)


class RestaurantRepository:
    """Manages indexing and in-memory queries for cleaned restaurant objects."""

    def __init__(self, restaurants: list[Restaurant]):
        self._restaurants = restaurants
        self._by_location = {}
        self._by_cuisine = {}
        self._by_budget_tier = {}
        self._is_ready = False
        self._build_indexes()

    def _build_indexes(self):
        """Processes the list of restaurants to construct indexes for fast queries."""
        logger.info("Building indexes for restaurant repository...")
        
        # Reset indexes
        self._by_location = {}
        self._by_cuisine = {}
        self._by_budget_tier = {
            BudgetTier.LOW: [],
            BudgetTier.MEDIUM: [],
            BudgetTier.HIGH: [],
        }

        for r in self._restaurants:
            # Index by location (normalized to lowercase)
            loc_key = r.location.strip().lower()
            if loc_key not in self._by_location:
                self._by_location[loc_key] = []
            self._by_location[loc_key].append(r)

            # Index by cuisine (individual cuisines are already lowercase lists)
            for cuisine in r.cuisine:
                c_key = cuisine.strip().lower()
                if c_key not in self._by_cuisine:
                    self._by_cuisine[c_key] = []
                self._by_cuisine[c_key].append(r)

            # Index by budget tier
            self._by_budget_tier[r.budget_tier].append(r)

        self._is_ready = True
        logger.info(
            f"Repository indexes built successfully. "
            f"Total restaurants: {len(self._restaurants)}, "
            f"Unique locations: {len(self._by_location)}, "
            f"Unique cuisines: {len(self._by_cuisine)}."
        )

    def get_all(self) -> list[Restaurant]:
        """Returns all restaurants in the repository."""
        return self._restaurants

    def get_by_location(self, location: str) -> list[Restaurant]:
        """Queries restaurants by their location (case-insensitive)."""
        loc_key = location.strip().lower()
        return self._by_location.get(loc_key, [])

    def get_known_locations(self) -> list[str]:
        """Returns sorted list of all unique locations present in the dataset."""
        return sorted(list(self._by_location.keys()))

    def get_known_cuisines(self) -> list[str]:
        """Returns sorted list of all unique cuisines present in the dataset."""
        return sorted(list(self._by_cuisine.keys()))

    def is_ready(self) -> bool:
        """Returns whether the repository indexes are built and ready to serve."""
        return self._is_ready
