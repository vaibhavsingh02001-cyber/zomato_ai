"""Application configuration loaded from environment variables."""

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings for the restaurant recommender."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    hf_dataset: str = Field(
        default="ManikaSaini/zomato-restaurant-recommendation",
        description="Hugging Face dataset identifier",
    )
    groq_api_key: str = Field(default="", description="GroqCloud API key")
    groq_model: str = Field(
        default="llama-3.3-70b-versatile",
        description="Groq model for recommendations",
    )
    max_candidates: int = Field(default=20, ge=1, le=100)
    top_recommendations: int = Field(default=5, ge=1, le=20)
    use_local_dataset: bool = Field(
        default=True,
        description="Whether to use local sample dataset instead of Hugging Face"
    )


    @field_validator("top_recommendations")
    @classmethod
    def top_recommendations_not_exceed_max_candidates(cls, value: int, info) -> int:
        max_candidates = info.data.get("max_candidates", 20)
        if value > max_candidates:
            msg = "top_recommendations cannot exceed max_candidates"
            raise ValueError(msg)
        return value


settings = Settings()
