"""Unit tests for the restaurant repository component."""

import pytest
from app.data.repository import RestaurantRepository
from app.models.preferences import BudgetTier
from app.models.restaurant import Restaurant


@pytest.fixture
def sample_restaurants():
    return [
        Restaurant(
            id="r_0001",
            name="Italian Delight",
            location="connaught place",
            cuisine=["italian", "pizza"],
            rating=4.2,
            estimated_cost="₹800 for two",
            budget_tier=BudgetTier.MEDIUM,
        ),
        Restaurant(
            id="r_0002",
            name="Spicy Tadka",
            location="connaught place",
            cuisine=["north indian", "mughlai"],
            rating=4.5,
            estimated_cost="₹500 for two",
            budget_tier=BudgetTier.MEDIUM,
        ),
        Restaurant(
            id="r_0003",
            name="Corner Café",
            location="hauz khas",
            cuisine=["café", "italian"],
            rating=3.9,
            estimated_cost="₹300 for two",
            budget_tier=BudgetTier.LOW,
        ),
    ]


def test_repository_initialization_and_ready(sample_restaurants):
    repo = RestaurantRepository(sample_restaurants)
    assert repo.is_ready()
    assert len(repo.get_all()) == 3


def test_repository_get_by_location(sample_restaurants):
    repo = RestaurantRepository(sample_restaurants)
    
    # Check exact case match
    delhi_results = repo.get_by_location("connaught place")
    assert len(delhi_results) == 2
    assert {r.name for r in delhi_results} == {"Italian Delight", "Spicy Tadka"}

    # Check case-insensitivity and whitespace trim
    bangalore_results = repo.get_by_location("  HAUZ KHAS  ")
    assert len(bangalore_results) == 1
    assert bangalore_results[0].name == "Corner Café"

    # Check empty query
    unknown_results = repo.get_by_location("mumbai")
    assert len(unknown_results) == 0


def test_repository_get_known_locations(sample_restaurants):
    repo = RestaurantRepository(sample_restaurants)
    locations = repo.get_known_locations()
    assert locations == ["connaught place", "hauz khas"]


def test_repository_get_known_cuisines(sample_restaurants):
    repo = RestaurantRepository(sample_restaurants)
    cuisines = repo.get_known_cuisines()
    assert cuisines == ["café", "italian", "mughlai", "north indian", "pizza"]
