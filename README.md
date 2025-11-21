# B2B Meeting Assistant
B2B Meeting Assistant is an internal tool that helps a telco sales team prepare B2B client meetings by centralizing and enriching client & market data, surfacing the most relevant insights and personalised recommendations, and producing compact meeting reports that can be used in-call. The assistant aggregates internal sources (CRM, financials) and external signals (company news, sector trends) and exposes them through a FastAPI backend and a Streamlit frontend.

---

# Code Structure
```
b2b-meeting-assistant/
│
├── backend/                            # FastAPI backend
│   ├── main.py                         # FastAPI application entrypoint
│   ├── fake_data.json                  # Stub data for services/testing.
│   ├── "Carte Identit\342\200\232.xlsx" # Raw internal client data file.
│   ├── "Etat des cr\303\207ances.xlsx" # Raw financial status data file.
│   ├── api/                            # FastAPI routers (versioned endpoints)
│   │   ├── cache_routes.py             # API routes for cache management.
│   │   ├── client_externe_data_routes.py # API routes for external client data.
│   │   ├── client_interne_data_routes.py # API routes for internal client data.
│   │   ├── client_search_routes.py     # API routes for client search functionality.
│   │   ├── debug_routes.py             # Utility routes for debugging.
│   │   ├── company_sheet_api.py
│   │   └── test_orm_api.py             # Temporary ORM testing routes.
│   └── services/                       # Business logic & external connectors
│       ├── rate_limiters/              # Shared rate limiting strategies
│       │   ├── global_concurrency_limiter.py # Cross-source concurrency guard
│       │   └── phantom_buster_rate_limiter.py # PhantomBuster-specific throttle for Linkedin
│       ├── db/                         # Data-access layer (SQLAlchemy engine + models)
│       │   ├── configdb.py             # Database connection configuration.
│       │   ├── database_engine.py      # FicheClient ORM + transactional session helpers
│       │   └── models/                 # ORM data models folder.
│       │       └── company_sheet_input.py # ORM model for client sheet input.
│       └── scrapping/                  # Website scraping pipeline and plugins
│           ├── base_plugin.py          # Plugin interface shared by scrapers
│           ├── plugin_manager.py       # Registry/factory for scraper plugins
│           ├── pipeline.py             # Orchestrates scraping, filtering & persistence
│           ├── embedding/              # Text embeddings for semantic similarity
│           │   ├── dataiku_embedding_engine.py # Dataiku-specific embedding engine.
│           │   └── embedding_engine.py
│           ├── filtering/              # Semantic filtering utilities
│           │   └── semantic_filtering_engine.py
│           └── plugins/
│               ├── linkedin.py         # Linkedin scraper
│               └── rss.py              # RSS scraper
│
├── frontend/                           # Streamlit app
│   ├── app.py                          # Streamlit app entrypoint
│   ├── models/                         # Data models and business logic
│   │   └── company_sheet.py
│   ├── components/                     # Reusable UI components (cards, tables, charts)
│   │   ├── header.py
│   │   ├── search_bar.py
│   │   ├── identity_card.py
│   │   ├── contact_section.py
│   │   ├── credit_status.py
│   │   ├── partnership_description.py
│   │   ├── revenue_chart.py
│   │   ├── complaints_section.py
│   │   ├── news_section.py
│   │   └── offers_potential.py
│   ├── services/                       # Frontend communication services.
│   │   └── api_client.py               # HTTP client for backend API.
│   └── static/                         # Static assets
│       ├── styles.css
│       └── logo.svg                    # Application logo file.
│
├── config/                             # Global configuration files.
│   ├── config.yaml                     # Configuration
│   └── config.py                       # Data classes + ConfigLoader using OmegaConf
│
├── docker/                             # Consolidated Docker build files.
│   ├── Dockerfile.backend              # Dockerfile for the backend service.
│   └── Dockerfile.frontend             # Dockerfile for the frontend service.
│
├── tests/                              # CI / integration test helpers and fixtures
│   ├── data/                           # Data used for testing purposes.
│   ├── integration/                    # Integration tests.
│   └── unit/                           # Isolated unit tests.
│
├── .dockerignore                       # Files/folders to exclude from Docker images.
├── docker-compose.yml                  # Docker service definition and orchestration.
├── Makefile                            # Automation tasks (build, test, production setup, Orange registry push).
├── .pre-commit-config.yaml             # pre-commit hooks (lint, format, safety)
├── pyproject.toml                      # Project dependencies, metadata, and tool configuration.
├── README.md
└── .gitignore
```

---

## Backend architecture highlights

- **Service layer**: `backend/services/` groups business logic by concern (scraping, data access, rate limiting) and is consumed by the FastAPI routers so the HTTP layer stays slim.
- **Data access**: `backend/services/db/database_engine.py` centralises SQLAlchemy setup, exposes the `FicheClient` ORM model, and provides a context-managed session helper to guarantee commits/rollbacks with structured logging via Loguru.
- **Scraping pipeline**: `backend/services/scrapping/` implements a plugin-driven ingestion flow. `pipeline.py` orchestrates each `BasePlugin` implementation, applies semantic filtering/embedding, and relies on the data layer to persist insights.
- **Configuration**: `config/` wraps config loading/validation so both backend and scraping jobs use a shared source of truth driven by `config.yaml`.

---

# Installation & setup (developer environment)

This project uses `uv` as the project manager for dependency resolution and virtual environment handling.

> If you haven't installed `uv` yet, install it following the official docs: [uv installation](https://docs.astral.sh/uv/getting-started/installation/)

### Clone repository
```bash
git clone https://github.com/artefactory-ma/b2b-meeting-assistant.git
cd b2b-meeting-assistant
```

### Install dependencies with `uv`

* **If you are on the Orange network**, run:

```bash
uv sync --all-extras --index https://repos.tech.orange/artifactory/api/pypi/pythonproxy/simple/
# Creates .venv and installs dependencies
```

* **Otherwise**, run:

```bash
uv sync --all-extras
# Creates .venv and installs dependencies
```

> Use `uv run` to execute commands inside the environment without manual activation.

### Pre-commit setup

Install hooks so linting/formatting runs locally:
```bash
uv run pre-commit install
```

---

# How to run the code & required configuration (dev + local run)

> The system comprises two primary components: **backend (FastAPI)** and **frontend (Streamlit)**. Below are step-by-step instructions to run both locally

### Start backend (development)

```bash
uv run --directory backend uvicorn main:app --reload
```

### Start frontend (development)

```bash
uv run --directory frontend streamlit run app.py
```

>* The Streamlit app should call the backend endpoints (e.g. `http://localhost:8000`).
>* If you use CORS, ensure backend accepts requests from `localhost:8501`.
