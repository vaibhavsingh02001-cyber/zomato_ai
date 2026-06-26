"""Unit tests for the LLM response parser."""

import pytest
from app.llm.parser import ResponseParser
from app.models.preferences import BudgetTier
from app.models.restaurant import Restaurant


@pytest.fixture
def candidate_pool():
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


def test_parser_valid_clean_json(candidate_pool):
    parser = ResponseParser()
    raw_text = """
    {
      "summary": "These are great Italian options in Delhi.",
      "recommendations": [
        {
          "rank": 1,
          "restaurant_id": "r_0002",
          "name": "Wrong Name Hallucination",
          "cuisine": "Wrong Cuisine",
          "rating": 5.0,
          "estimated_cost": "₹100",
          "explanation": "Great slice of pizza."
        },
        {
          "rank": 2,
          "restaurant_id": "r_0001",
          "name": "Italian Cafe",
          "cuisine": "italian",
          "rating": 4.2,
          "estimated_cost": "₹800 for two",
          "explanation": "Cosy place."
        }
      ]
    }
    """
    response = parser.parse(raw_text, candidate_pool)
    assert response.summary == "These are great Italian options in Delhi."
    assert len(response.recommendations) == 2
    
    # Verify that hallucinated structured fields (name, cuisine, rating, estimated_cost)
    # were overwritten by source of truth values from candidate_pool
    rec1 = response.recommendations[0]
    assert rec1.rank == 1
    assert rec1.restaurant_id == "r_0002"
    assert rec1.name == "Pizza Place"  # Overwritten!
    assert rec1.cuisine == "italian, pizza"  # Overwritten!
    assert rec1.rating == 4.5  # Overwritten!
    assert rec1.estimated_cost == "₹600 for two"  # Overwritten!
    assert rec1.explanation == "Great slice of pizza."  # Kept!


def test_parser_with_markdown_fences(candidate_pool):
    parser = ResponseParser()
    raw_text = """```json
    {
      "summary": "Quick summary",
      "recommendations": [
        {
          "rank": 1,
          "restaurant_id": "r_0001",
          "name": "Italian Cafe",
          "cuisine": "italian",
          "rating": 4.2,
          "estimated_cost": "₹800 for two",
          "explanation": "Nice place."
        }
      ]
    }
    ```"""
    response = parser.parse(raw_text, candidate_pool)
    assert len(response.recommendations) == 1
    assert response.recommendations[0].restaurant_id == "r_0001"


def test_parser_invalid_json(candidate_pool):
    parser = ResponseParser()
    raw_text = "{ malformed json "
    with pytest.raises(ValueError) as exc:
        parser.parse(raw_text, candidate_pool)
    assert "Failed to parse LLM output as JSON" in str(exc.value)


def test_parser_missing_required_keys(candidate_pool):
    parser = ResponseParser()
    # Missing 'recommendations' array key
    raw_text = """
    {
      "summary": "Missing array"
    }
    """
    with pytest.raises(ValueError) as exc:
        parser.parse(raw_text, candidate_pool)
    assert "LLM JSON schema mismatch" in str(exc.value)


def test_parser_filters_hallucinated_ids(candidate_pool):
    parser = ResponseParser()
    raw_text = """
    {
      "summary": "Contains one hallucinated ID.",
      "recommendations": [
        {
          "rank": 1,
          "restaurant_id": "r_9999",
          "name": "Hallucinated Palace",
          "cuisine": "Fairy",
          "rating": 5.0,
          "estimated_cost": "₹10",
          "explanation": "This ID does not exist in the candidates."
        },
        {
          "rank": 2,
          "restaurant_id": "r_0001",
          "name": "Italian Cafe",
          "cuisine": "italian",
          "rating": 4.2,
          "estimated_cost": "₹800 for two",
          "explanation": "This ID is valid."
        }
      ]
    }
    """
    response = parser.parse(raw_text, candidate_pool)
    # The hallucinated ID should be dropped, leaving exactly 1 recommendation
    assert len(response.recommendations) == 1
    
    # Ranks should be re-indexed starting from 1
    assert response.recommendations[0].restaurant_id == "r_0001"
    assert response.recommendations[0].rank == 1
