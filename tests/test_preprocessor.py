"""Unit tests for the preprocessor component."""

import pytest
from app.data.preprocessor import Preprocessor
from app.models.preferences import BudgetTier


def test_preprocessor_happy_path():
    preprocessor = Preprocessor()
    raw_data = [
        {
            "name": "Trattoria Roma",
            "location": "Delhi",
            "cuisines": "Italian, Pizza",
            "rate": "4.3/5",
            "approx_cost(for two people)": "₹800 for two",
        }
    ]
    results = preprocessor.preprocess(raw_data)
    assert len(results) == 1
    restaurant = results[0]
    assert restaurant.id == "r_0001"
    assert restaurant.name == "Trattoria Roma"
    assert restaurant.location == "delhi"
    assert restaurant.cuisine == ["italian", "pizza"]
    assert restaurant.rating == 4.3
    assert restaurant.estimated_cost == "₹800 for two"
    assert restaurant.budget_tier == BudgetTier.MEDIUM


def test_preprocessor_column_mapping_variants():
    preprocessor = Preprocessor()
    raw_data = [
        {
            "Restaurant_Name": "Taco Place",
            "Place_Name": "CP",
            "Cuisine": "Mexican",
            "rating": "3.8",
            "Cost": "300",
        }
    ]
    results = preprocessor.preprocess(raw_data)
    assert len(results) == 1
    restaurant = results[0]
    assert restaurant.name == "Taco Place"
    # should be canonicalized to 'connaught place' from 'CP'
    assert restaurant.location == "connaught place"
    assert restaurant.cuisine == ["mexican"]
    assert restaurant.rating == 3.8
    assert restaurant.estimated_cost == "₹300 for two"
    assert restaurant.budget_tier == BudgetTier.LOW


def test_preprocessor_drops_missing_required_fields():
    preprocessor = Preprocessor()
    raw_data = [
        # Missing name
        {
            "location": "Delhi",
            "cuisines": "Italian",
            "rate": "4.0",
            "cost": "500",
        },
        # Missing location
        {
            "name": "Test",
            "cuisines": "Italian",
            "rate": "4.0",
            "cost": "500",
        },
        # Missing cuisines
        {
            "name": "Test",
            "location": "Delhi",
            "rate": "4.0",
            "cost": "500",
        },
        # Missing rating
        {
            "name": "Test",
            "location": "Delhi",
            "cuisines": "Italian",
            "cost": "500",
        },
        # Missing cost
        {
            "name": "Test",
            "location": "Delhi",
            "cuisines": "Italian",
            "rate": "4.0",
        },
    ]
    results = preprocessor.preprocess(raw_data)
    assert len(results) == 0


def test_preprocessor_rating_parsing_and_clamping():
    preprocessor = Preprocessor()
    raw_data = [
        # Invalid rating
        {
            "name": "R1",
            "location": "Delhi",
            "cuisines": "Italian",
            "rate": "NEW",
            "cost": "500",
        },
        # Invalid rating 2
        {
            "name": "R2",
            "location": "Delhi",
            "cuisines": "Italian",
            "rate": "-",
            "cost": "500",
        },
        # Out of bounds rating (clamping expected or dropping depending on rules; we clamp)
        {
            "name": "R3",
            "location": "Delhi",
            "cuisines": "Italian",
            "rate": "6.0",
            "cost": "500",
        },
        # Negative rating (clamped to 0.0)
        {
            "name": "R4",
            "location": "Delhi",
            "cuisines": "Italian",
            "rate": "-1.5",
            "cost": "500",
        },
    ]
    results = preprocessor.preprocess(raw_data)
    # R1 and R2 should be dropped. R3 and R4 clamped.
    assert len(results) == 2
    
    r3 = next(r for r in results if r.name == "R3")
    assert r3.rating == 5.0

    r4 = next(r for r in results if r.name == "R4")
    assert r4.rating == 0.0


def test_preprocessor_cost_parsing_and_tiers():
    preprocessor = Preprocessor()
    raw_data = [
        # Low tier
        {
            "name": "Low",
            "location": "Delhi",
            "cuisines": "Street Food",
            "rate": "4.0",
            "cost": "₹350 for two",
        },
        # Medium tier
        {
            "name": "Medium",
            "location": "Delhi",
            "cuisines": "Street Food",
            "rate": "4.0",
            "cost": "1000",
        },
        # High tier
        {
            "name": "High",
            "location": "Delhi",
            "cuisines": "Street Food",
            "rate": "4.0",
            "cost": "1,200",
        },
    ]
    results = preprocessor.preprocess(raw_data)
    assert len(results) == 3
    
    low = next(r for r in results if r.name == "Low")
    assert low.budget_tier == BudgetTier.LOW
    assert low.estimated_cost == "₹350 for two"

    med = next(r for r in results if r.name == "Medium")
    assert med.budget_tier == BudgetTier.MEDIUM
    assert med.estimated_cost == "₹1000 for two"

    high = next(r for r in results if r.name == "High")
    assert high.budget_tier == BudgetTier.HIGH
    assert high.estimated_cost == "₹1200 for two"


def test_preprocessor_deduplication():
    preprocessor = Preprocessor()
    raw_data = [
        # Same restaurant and location, first has rating 4.0, second 4.5
        {
            "name": "Duplicate Café",
            "location": "Delhi",
            "cuisines": "Café",
            "rate": "4.0",
            "cost": "500",
        },
        {
            "name": "Duplicate Café",
            "location": "Delhi",
            "cuisines": "Café",
            "rate": "4.5",
            "cost": "500",
        },
    ]
    results = preprocessor.preprocess(raw_data)
    assert len(results) == 1
    # Check that the one with higher rating was kept
    assert results[0].rating == 4.5
    assert results[0].id == "r_0001"
