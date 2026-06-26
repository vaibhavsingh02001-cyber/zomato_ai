"""FastAPI main entrypoint for the AI-Powered Restaurant Recommendation System."""

import logging
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.data.loader import DatasetLoader
from app.data.preprocessor import Preprocessor
from app.data.repository import RestaurantRepository
from app.controllers.recommendation_controller import RecommendationController
from app.models.preferences import BudgetTier
from app.models.recommendation import RecommendationResponse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class RecommendRequest(BaseModel):
    """API request model for restaurant recommendations."""

    location: str = Field(..., description="Delhi sub-area (e.g., Connaught Place, Hauz Khas)")
    budget: BudgetTier = Field(..., description="Budget tier: low, medium, high")
    cuisine: str = Field(..., description="Preferred cuisine (e.g., Italian, Chinese)")
    min_rating: float = Field(0.0, ge=0.0, le=5.0, description="Minimum restaurant rating")
    additional_preferences: str | None = Field(None, description="Free text for custom preferences")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle events to load dataset and prepare repository on startup."""
    logger.info("Initializing restaurant recommendation system dataset...")
    try:
        # Load dataset
        loader = DatasetLoader()
        raw_rows = loader.load_raw_dataset()

        # Clean and preprocess dataset
        preprocessor = Preprocessor()
        cleaned_restaurants = preprocessor.preprocess(raw_rows)

        # Build repository and controllers
        repository = RestaurantRepository(cleaned_restaurants)
        controller = RecommendationController(repository)

        # Store in app state
        app.state.repository = repository
        app.state.controller = controller
        app.state.is_ready = True
        logger.info("Application initialization complete and repository is ready.")
    except Exception as e:
        logger.exception("Failed to initialize dataset during startup lifespans.")
        app.state.is_ready = False
        # Do not block startup, but handle queries gracefully
    
    yield
    logger.info("Shutting down application...")


app = FastAPI(
    title="AI-Powered Restaurant Recommender",
    description="A Zomato-inspired restaurant recommendation engine using FastAPI and Groq.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def check_ready_middleware(request: Request, call_next):
    """Ensures dataset initialization is complete before serving queries."""
    # Allow health checks and static files even if database isn't ready
    path = request.url.path
    if path == "/health" or path.startswith("/static"):
        return await call_next(request)
        
    is_ready = getattr(request.app.state, "is_ready", False)
    if not is_ready:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"detail": "Application database is initializing. Please try again shortly."},
        )
    return await call_next(request)


# Custom exception handlers for clean JSON API contracts
@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    logger.warning(f"Validation error: {exc}")
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": str(exc)},
    )


@app.exception_handler(LookupError)
async def lookup_error_handler(request: Request, exc: LookupError):
    logger.warning(f"Lookup error: {exc}")
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={"detail": str(exc)},
    )


# API Endpoints
@app.get("/health", tags=["Status"])
async def health_check():
    """Checks the health of the API and dataset initialization status."""
    is_ready = getattr(app.state, "is_ready", False)
    if not is_ready:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "initializing", "detail": "Dataset loading in progress"},
        )
    
    repo: RestaurantRepository = app.state.repository
    return {
        "status": "healthy",
        "dataset": {
            "loaded": True,
            "restaurant_count": len(repo.get_all()),
            "locations_count": len(repo.get_known_locations()),
            "cuisines_count": len(repo.get_known_cuisines()),
        }
    }


@app.get("/api/v1/locations", tags=["Metadata"])
async def get_locations():
    """Returns the list of unique, known restaurant locations in the repository."""
    repo: RestaurantRepository = app.state.repository
    return repo.get_known_locations()


@app.get("/api/v1/cuisines", tags=["Metadata"])
async def get_cuisines():
    """Returns the list of unique, known cuisines in the repository."""
    repo: RestaurantRepository = app.state.repository
    return repo.get_known_cuisines()


@app.post("/api/v1/recommend", response_model=RecommendationResponse, tags=["Recommendations"])
async def recommend(request_data: RecommendRequest):
    """Generates structured, AI-ranked restaurant recommendations based on user preferences."""
    controller: RecommendationController = app.state.controller
    # Convert incoming body model to raw dict for the controller
    raw_prefs = request_data.model_dump()
    response = controller.get_recommendations(raw_prefs)
    return response


# Static file serving for Frontend UI (Phase 5)
static_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "ui", "static"))

# Ensure static directory exists
os.makedirs(static_dir, exist_ok=True)

# Serve static assets
app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/", include_in_schema=False)
async def serve_ui():
    """Serves the single-page application landing page."""
    index_file = os.path.join(static_dir, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return JSONResponse(
        content={"message": "Frontend UI is under development. Please check back in Phase 5!"}
    )
