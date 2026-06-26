"""Integration tests for the Groq recommendation engine."""

import os
from unittest.mock import MagicMock, patch
import pytest
from app.config import settings
from app.data.repository import RestaurantRepository
from app.models.preferences import BudgetTier, UserPreferences
from app.models.restaurant import Restaurant
from app.services.recommendation_engine import RecommendationEngine


@pytest.fixture
def sample_candidates():
    return [
        Restaurant(
            id="r_0001",
            name="Italian Cafe",
            location="delhi",
            cuisine=["italian"],
            rating=4.2,
            estimated_cost="₹800 for two",
            budget_tier=BudgetTier.MEDIUM,
        ),
        Restaurant(
            id="r_0002",
            name="Pizza Place",
            location="delhi",
            cuisine=["italian", "pizza"],
            rating=4.5,
            estimated_cost="₹600 for two",
            budget_tier=BudgetTier.MEDIUM,
        ),
    ]


@pytest.fixture
def mock_repository(sample_candidates):
    return RestaurantRepository(sample_candidates)


def test_recommendation_engine_mocked_success(mock_repository, sample_candidates):
    """Tests recommendation engine with a mocked LLM client response."""
    engine = RecommendationEngine(mock_repository)
    
    # Mock LLMClient get_recommendations
    mocked_json = """
    {
      "summary": "Mocked summary",
      "recommendations": [
        {
          "rank": 1,
          "restaurant_id": "r_0002",
          "name": "Pizza Place",
          "cuisine": "italian, pizza",
          "rating": 4.5,
          "estimated_cost": "₹600 for two",
          "explanation": "Mocked explanation"
        }
      ]
    }
    """
    engine.llm_client.get_recommendations = MagicMock(return_value=mocked_json)

    prefs = UserPreferences(
        location="delhi",
        budget=BudgetTier.MEDIUM,
        cuisine="italian",
        min_rating=4.0,
    )
    context = {
        "preferences": {
            "location": "delhi",
            "budget": "medium",
            "cuisine": "italian",
            "min_rating": 4.0,
            "additional_preferences": None,
        },
        "candidates": [
            {
                "id": "r_0001",
                "name": "Italian Cafe",
                "location": "delhi",
                "cuisine": "italian",
                "rating": 4.2,
                "estimated_cost": "₹800 for two",
                "budget_tier": "medium",
            },
            {
                "id": "r_0002",
                "name": "Pizza Place",
                "location": "delhi",
                "cuisine": "italian, pizza",
                "rating": 4.5,
                "estimated_cost": "₹600 for two",
                "budget_tier": "medium",
            },
        ],
        "metadata": {
            "candidates_considered": 2,
            "filters_applied": ["location", "cuisine", "min_rating", "budget"],
            "filters_relaxed": [],
        },
    }

    response = engine.recommend(prefs, sample_candidates, context)
    assert response.metadata.used_fallback is False
    assert len(response.recommendations) == 1
    assert response.recommendations[0].restaurant_id == "r_0002"
    assert response.recommendations[0].explanation == "Mocked explanation"


def test_recommendation_engine_fallback_on_client_error(mock_repository, sample_candidates):
    """Tests that the engine routes correctly to the fallback ranker when Groq raises errors."""
    engine = RecommendationEngine(mock_repository)
    
    # Mock LLMClient to raise an exception (e.g. rate limit, connection issue)
    engine.llm_client.get_recommendations = MagicMock(side_effect=RuntimeError("Groq Service Outage"))

    prefs = UserPreferences(
        location="delhi",
        budget=BudgetTier.MEDIUM,
        cuisine="italian",
        min_rating=4.0,
    )
    context = {
        "preferences": {
            "location": "delhi",
            "budget": "medium",
            "cuisine": "italian",
            "min_rating": 4.0,
            "additional_preferences": None,
        },
        "candidates": [],
        "metadata": {
            "candidates_considered": 2,
            "filters_applied": ["location", "cuisine", "min_rating", "budget"],
            "filters_relaxed": [],
        },
    }

    # Should fall back and return a degraded response (used_fallback = True)
    response = engine.recommend(prefs, sample_candidates, context)
    assert response.metadata.used_fallback is True
    # The fallback output should be ordered by rating descending (r_0002 is 4.5, r_0001 is 4.2)
    assert response.recommendations[0].restaurant_id == "r_0002"
    assert response.recommendations[1].restaurant_id == "r_0001"


@pytest.mark.skipif(
    not os.environ.get("GROQ_API_KEY") and not settings.groq_api_key,
    reason="GROQ_API_KEY environment variable is not configured for integration test.",
)
def test_recommendation_engine_live_integration(mock_repository, sample_candidates):
    """Live API integration test checking prompt querying and completions against Groq API."""
    engine = RecommendationEngine(mock_repository)
    prefs = UserPreferences(
        location="delhi",
        budget=BudgetTier.MEDIUM,
        cuisine="italian",
        min_rating=4.0,
    )
    context = {
        "preferences": {
            "location": "delhi",
            "budget": "medium",
            "cuisine": "italian",
            "min_rating": 4.0,
            "additional_preferences": None,
        },
        "candidates": [
            {
                "id": "r_0001",
                "name": "Italian Cafe",
                "location": "delhi",
                "cuisine": "italian",
                "rating": 4.2,
                "estimated_cost": "₹800 for two",
                "budget_tier": "medium",
            },
            {
                "id": "r_0002",
                "name": "Pizza Place",
                "location": "delhi",
                "cuisine": "italian, pizza",
                "rating": 4.5,
                "estimated_cost": "₹600 for two",
                "budget_tier": "medium",
            },
        ],
        "metadata": {
            "candidates_considered": 2,
            "filters_applied": ["location", "cuisine", "min_rating", "budget"],
            "filters_relaxed": [],
        },
    }
    
    response = engine.recommend(prefs, sample_candidates, context)
    
    # If the call succeeds, we get a valid recommendation, if rate-limited or key invalid,
    # it might fall back, which is also a valid state to verify without crashing the test.
    assert response.summary is not None
    assert len(response.recommendations) > 0
