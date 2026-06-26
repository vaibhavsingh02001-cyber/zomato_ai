"""Unit tests for the preference service."""

import pytest
from app.data.repository import RestaurantRepository
from app.models.preferences import BudgetTier
from app.models.restaurant import Restaurant
from app.services.preference_service import PreferenceService


@pytest.fixture
def mock_repository():
    """Returns a repository loaded with basic mock records for validation checks."""
    restaurants = [
        Restaurant(
            id="r_1",
            name="R1",
            location="connaught place",
            cuisine=["italian", "pizza"],
            rating=4.0,
            estimated_cost="₹500",
            budget_tier=BudgetTier.MEDIUM,
        ),
        Restaurant(
            id="r_2",
            name="R2",
            location="hauz khas",
            cuisine=["south indian"],
            rating=4.5,
            estimated_cost="₹300",
            budget_tier=BudgetTier.LOW,
        ),
    ]
    return RestaurantRepository(restaurants)


def test_preference_service_happy_path(mock_repository):
    service = PreferenceService(mock_repository)
    raw = {
        "location": "Connaught Place",
        "budget": "medium",
        "cuisine": "Italian",
        "min_rating": 3.5,
        "additional_preferences": "rooftop dining",
    }
    prefs = service.validate(raw)
    assert prefs.location == "connaught place"
    assert prefs.budget == BudgetTier.MEDIUM
    assert prefs.cuisine == "italian"
    assert prefs.min_rating == 3.5
    assert prefs.additional_preferences == "rooftop dining"


def test_preference_service_fuzzy_cuisine_match(mock_repository):
    service = PreferenceService(mock_repository)
    
    # "italy" should fuzzy match "italian" (close match cutoff 0.5)
    raw1 = {"location": "Connaught Place", "budget": "medium", "cuisine": "italy"}
    prefs1 = service.validate(raw1)
    assert prefs1.cuisine == "italian"

    # "south" should match "south indian" (substring check)
    raw2 = {"location": "Hauz Khas", "budget": "low", "cuisine": "south"}
    prefs2 = service.validate(raw2)
    assert prefs2.cuisine == "south indian"


def test_preference_service_rejects_unknown_location(mock_repository):
    service = PreferenceService(mock_repository)
    raw = {"location": "Mumbai", "budget": "medium", "cuisine": "Italian"}
    with pytest.raises(ValueError) as exc:
        service.validate(raw)
    assert "location 'Mumbai' is not available" in str(exc.value)


def test_preference_service_rejects_invalid_budget(mock_repository):
    service = PreferenceService(mock_repository)
    raw = {"location": "Connaught Place", "budget": "cheap", "cuisine": "Italian"}
    with pytest.raises(ValueError) as exc:
        service.validate(raw)
    assert "budget must be one of" in str(exc.value)


def test_preference_service_rejects_unknown_cuisine(mock_repository):
    service = PreferenceService(mock_repository)
    raw = {"location": "Connaught Place", "budget": "medium", "cuisine": "Mexican"}
    with pytest.raises(ValueError) as exc:
        service.validate(raw)
    assert "cuisine 'Mexican' matches no known cuisines" in str(exc.value)


def test_preference_service_sanitizes_additional_preferences(mock_repository):
    service = PreferenceService(mock_repository)
    
    # Test control chars removal
    raw1 = {
        "location": "Connaught Place",
        "budget": "medium",
        "cuisine": "Italian",
        "additional_preferences": "line1\nline2\x00test",
    }
    prefs1 = service.validate(raw1)
    # Control characters (including \n and \x00) should be stripped
    assert prefs1.additional_preferences == "line1line2test"

    # Test truncation to 500 characters
    long_text = "a" * 600
    raw2 = {
        "location": "Connaught Place",
        "budget": "medium",
        "cuisine": "Italian",
        "additional_preferences": long_text,
    }
    prefs2 = service.validate(raw2)
    assert len(prefs2.additional_preferences) == 500
    assert prefs2.additional_preferences == "a" * 500
