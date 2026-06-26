# Restaurant Recommender

AI-powered restaurant recommendation service inspired by Zomato. Combines structured Zomato dataset filtering with Groq LLM ranking and explanations.

## Prerequisites

- Python 3.11+
- [Groq API key](https://console.groq.com) (required from Phase 3 onward)

## Setup

```bash
# Clone or navigate to the project directory
cd restaurant-recommender

# Create and activate a virtual environment
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
# source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
copy .env.example .env   # Windows
# cp .env.example .env   # macOS / Linux

# Edit .env and set GROQ_API_KEY when implementing LLM features
```

## Verify installation (Phase 0)

```bash
python -c "from app.config import settings; print(settings.groq_model)"
pytest tests/ -v
```

## Project structure

```
restaurant-recommender/
├── app/
│   ├── config.py           # Environment-based settings
│   └── models/             # Domain models (Restaurant, UserPreferences, etc.)
├── tests/                  # Unit tests
├── docs/                   # Design documents
├── .env.example
├── requirements.txt
└── README.md
```

## Documentation

| Document | Description |
|----------|-------------|
| [docs/context.md](docs/context.md) | Project objectives and success criteria |
| [docs/architecture.md](docs/architecture.md) | System design and Groq integration |
| [docs/implementation-plan.md](docs/implementation-plan.md) | Phase-wise build plan |
| [docs/edge-case.md](docs/edge-case.md) | Corner scenarios and test matrix |

## Implementation phases

| Phase | Status | Description |
|-------|--------|-------------|
| P0 | Done | Project setup, config, domain models |
| P1 | Pending | Data pipeline (Hugging Face dataset) |
| P2 | Pending | Filtering and preferences |
| P3 | Pending | Groq recommendation engine |
| P4 | Pending | FastAPI + Streamlit UI |
| P5 | Pending | Polish and hardening |

## Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `HF_DATASET` | `ManikaSaini/zomato-restaurant-recommendation` | Hugging Face dataset |
| `GROQ_API_KEY` | — | GroqCloud API key |
| `GROQ_MODEL` | `llama-3.3-70b-versatile` | Groq model name |
| `MAX_CANDIDATES` | `20` | Max restaurants sent to LLM |
| `TOP_RECOMMENDATIONS` | `5` | Recommendations returned to user |

## License

MIT (or your chosen license)
