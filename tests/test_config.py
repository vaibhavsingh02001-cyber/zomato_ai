"""Tests for application configuration."""

from app.config import Settings


def test_settings_load_with_defaults():
    settings = Settings(_env_file=None)
    assert settings.hf_dataset == "ManikaSaini/zomato-restaurant-recommendation"
    assert settings.groq_model == "llama-3.3-70b-versatile"
    assert settings.max_candidates == 20
    assert settings.top_recommendations == 5


def test_settings_load_from_env(monkeypatch):
    monkeypatch.setenv("HF_DATASET", "custom/dataset")
    monkeypatch.setenv("GROQ_MODEL", "llama-3.1-8b-instant")
    monkeypatch.setenv("MAX_CANDIDATES", "15")
    monkeypatch.setenv("TOP_RECOMMENDATIONS", "3")

    settings = Settings(_env_file=None)
    assert settings.hf_dataset == "custom/dataset"
    assert settings.groq_model == "llama-3.1-8b-instant"
    assert settings.max_candidates == 15
    assert settings.top_recommendations == 3
