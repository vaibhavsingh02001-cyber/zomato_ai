"""Tests for domain models."""

import pytest
from pydantic import ValidationError

from app.models import (
    BudgetTier,
    Recommendation,
    RecommendationResponse,
    Restaurant,
    UserPreferences,
)


def test_user_preferences_validates_sample_json():
    prefs = UserPreferences.model_validate(
        {
            "location": "Delhi",
            "budget": "medium",
            "cuisine": "Italian",
            "min_rating": 4.0,
            "additional_preferences": "family-friendly, quick service",
        }
    )
    assert prefs.location == "Delhi"
    assert prefs.budget == BudgetTier.MEDIUM
    assert prefs.min_rating == 4.0


def test_user_preferences_rejects_invalid_budget():
    with pytest.raises(ValidationError):
        UserPreferences.model_validate(
            {
                "location": "Delhi",
                "budget": "cheap",
                "cuisine": "Italian",
            }
        )


def test_user_preferences_rejects_empty_location():
    with pytest.raises(ValidationError):
        UserPreferences.model_validate(
            {
                "location": "   ",
                "budget": "low",
                "cuisine": "Chinese",
            }
        )


def test_restaurant_validates_sample_data():
    restaurant = Restaurant.model_validate(
        {
            "id": "r_1042",
            "name": "Trattoria Roma",
            "location": "delhi",
            "cuisine": ["italian", "pizza"],
            "rating": 4.3,
            "estimated_cost": "₹800 for two",
            "budget_tier": "medium",
        }
    )
    assert restaurant.id == "r_1042"
    assert restaurant.budget_tier == BudgetTier.MEDIUM


def test_recommendation_response_validates_sample_json():
    response = RecommendationResponse.model_validate(
        {
            "summary": "Based on your preference for Italian food in Delhi...",
            "recommendations": [
                {
                    "rank": 1,
                    "restaurant_id": "r_1042",
                    "name": "Trattoria Roma",
                    "cuisine": "Italian",
                    "rating": 4.3,
                    "estimated_cost": "₹800 for two",
                    "explanation": "Highly rated Italian spot within your medium budget.",
                }
            ],
            "metadata": {
                "candidates_considered": 18,
                "filters_applied": ["location", "cuisine", "min_rating", "budget"],
            },
        }
    )
    assert len(response.recommendations) == 1
    assert response.recommendations[0].rank == 1


def test_recommendation_rejects_invalid_rating():
    with pytest.raises(ValidationError):
        Recommendation.model_validate(
            {
                "rank": 1,
                "restaurant_id": "r_1",
                "name": "Test",
                "cuisine": "Italian",
                "rating": 6.0,
                "estimated_cost": "₹500",
                "explanation": "Test explanation.",
            }
        )
