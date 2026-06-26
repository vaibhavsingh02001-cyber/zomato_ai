"""Unit tests for the fallback ranking engine."""

import pytest
from app.models.preferences import BudgetTier, UserPreferences
from app.models.restaurant import Restaurant
from app.services.fallback_ranker import FallbackRanker


@pytest.fixture
def candidate_restaurants():
    return [
        Restaurant(
            id="r_0001",
            name="Delhi Italian 1",
            location="delhi",
            cuisine=["italian"],
            rating=4.2,
            estimated_cost="₹800 for two",
            budget_tier=BudgetTier.MEDIUM,
        ),
        Restaurant(
            id="r_0002",
            name="Delhi Italian 2",
            location="delhi",
            cuisine=["italian", "pizza"],
            rating=4.5,
            estimated_cost="₹900 for two",
            budget_tier=BudgetTier.MEDIUM,
        ),
        Restaurant(
            id="r_0003",
            name="Delhi Chinese 1",
            location="delhi",
            cuisine=["chinese"],
            rating=3.9,
            estimated_cost="₹700 for two",
            budget_tier=BudgetTier.MEDIUM,
        ),
    ]


def test_fallback_ranker_ranking_and_explanations(candidate_restaurants):
    ranker = FallbackRanker()
    prefs = UserPreferences(
        location="delhi",
        budget=BudgetTier.MEDIUM,
        cuisine="italian",
        min_rating=4.0,
    )
    
    metadata = {
        "candidates_considered": 10,
        "filters_applied": ["location", "min_rating", "budget"],
        "filters_relaxed": ["cuisine"],
    }
    
    response = ranker.rank(prefs, candidate_restaurants, metadata=metadata)
    
    # Check that recommendations are returned and limited to top_recommendations (default: 5, but we have 3 candidates)
    assert len(response.recommendations) == 3
    assert response.metadata.used_fallback is True
    assert response.metadata.candidates_considered == 10
    assert response.metadata.filters_relaxed == ["cuisine"]

    # Verify sorting: r_0002 (4.5 rating) should be rank 1, r_0001 (4.2) rank 2, r_0003 (3.9) rank 3
    assert response.recommendations[0].restaurant_id == "r_0002"
    assert response.recommendations[0].rank == 1
    assert response.recommendations[1].restaurant_id == "r_0001"
    assert response.recommendations[1].rank == 2
    assert response.recommendations[2].restaurant_id == "r_0003"
    assert response.recommendations[2].rank == 3

    # Verify generated template explanation
    explanation = response.recommendations[0].explanation
    assert "Rated 4.5" in explanation
    assert "italian, pizza" in explanation
    assert "medium budget" in explanation
    assert "estimated cost of ₹900 for two" in explanation
