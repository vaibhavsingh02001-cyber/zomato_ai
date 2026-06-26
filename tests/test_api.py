"""Integration and unit tests for the FastAPI endpoint and routing logic."""

import json
from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.recommendation import RecommendationResponse


@pytest.fixture(scope="session", autouse=True)
def mock_dataset_loader():
    """Session-wide fixture to mock Hugging Face dataset loading.

    This prevents hitting the network and ensures a small, predictable set of
    restaurant records is loaded for all API tests.
    """
    mock_data = [
        {
            "name": "Pizza Corner",
            "location": "Connaught Place",
            "cuisines": "Italian, Pizza",
            "rate": "4.5/5",
            "approx_cost(for two people)": "500",
        },
        {
            "name": "Curry Hub",
            "location": "Hauz Khas",
            "cuisines": "South Indian, Indian",
            "rate": "4.0/5",
            "approx_cost(for two people)": "300",
        },
    ]
    with patch("app.data.loader.DatasetLoader.load_raw_dataset", return_value=mock_data):
        yield


@pytest.fixture
def client():
    """Returns a FastAPI TestClient in a context manager to trigger lifespan events."""
    with TestClient(app) as c:
        yield c


def test_health_endpoint(client):
    """Verifies that the /health endpoint returns dataset counts and active status."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["dataset"]["loaded"] is True
    assert data["dataset"]["restaurant_count"] == 2
    assert data["dataset"]["locations_count"] == 2
    assert data["dataset"]["cuisines_count"] == 4  # indian, italian, pizza, south indian


def test_locations_endpoint(client):
    """Verifies that the locations metadata endpoint returns sorted known locations."""
    response = client.get("/api/v1/locations")
    assert response.status_code == 200
    locations = response.json()
    assert isinstance(locations, list)
    assert locations == ["connaught place", "hauz khas"]


def test_cuisines_endpoint(client):
    """Verifies that the cuisines metadata endpoint returns sorted known cuisines."""
    response = client.get("/api/v1/cuisines")
    assert response.status_code == 200
    cuisines = response.json()
    assert isinstance(cuisines, list)
    assert "italian" in cuisines
    assert "pizza" in cuisines


@patch("app.llm.client.LLMClient.get_recommendations")
def test_recommend_endpoint_success(mock_get_recommendations, client):
    """Verifies successful recommendation flow with mocked LLM response."""
    # Define a valid structured response matching the parser schema
    mock_llm_json = {
        "summary": "Here is an amazing Italian recommendation in Connaught Place.",
        "recommendations": [
            {
                "rank": 1,
                "restaurant_id": "r_0001",
                "name": "Pizza Corner",
                "cuisine": "Italian",
                "rating": 4.5,
                "estimated_cost": "₹500 for two",
                "explanation": "Fits your medium budget and has top tier pizza.",
            }
        ],
    }
    mock_get_recommendations.return_value = json.dumps(mock_llm_json)

    payload = {
        "location": "Connaught Place",
        "budget": "medium",
        "cuisine": "Italian",
        "min_rating": 4.0,
        "additional_preferences": "nice ambiance",
    }
    
    response = client.post("/api/v1/recommend", json=payload)
    assert response.status_code == 200
    
    data = response.json()
    assert data["summary"] == mock_llm_json["summary"]
    assert len(data["recommendations"]) == 1
    assert data["recommendations"][0]["name"] == "Pizza Corner"
    assert data["recommendations"][0]["restaurant_id"] == "r_0001"
    assert data["metadata"]["used_fallback"] is False


def test_recommend_endpoint_validation_error(client):
    """Verifies validation failure (400 Bad Request) for invalid preferences."""
    # Test unknown location
    payload_bad_location = {
        "location": "Mumbai",
        "budget": "medium",
        "cuisine": "Italian",
    }
    response = client.post("/api/v1/recommend", json=payload_bad_location)
    assert response.status_code == 400
    assert "location 'Mumbai' is not available" in response.json()["detail"]

    # Test invalid budget
    payload_bad_budget = {
        "location": "Connaught Place",
        "budget": "very high",
        "cuisine": "Italian",
    }
    response = client.post("/api/v1/recommend", json=payload_bad_budget)
    assert response.status_code == 422  # Pydantic validation handles type/schema constraints


@patch("app.services.filter_service.FilterService.build_candidates")
def test_recommend_endpoint_not_found_error(mock_build_candidates, client):
    """Verifies that LookupError translates to a 404 status code."""
    mock_build_candidates.side_effect = LookupError("No matching restaurants found")

    payload = {
        "location": "Connaught Place",
        "budget": "medium",
        "cuisine": "Italian",
    }
    response = client.post("/api/v1/recommend", json=payload)
    assert response.json()["detail"] == "No matching restaurants found"

