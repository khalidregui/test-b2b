# main.py

from backend.api import (
    cache_routes,
    client_externe_data_routes,
    client_interne_data_routes,
    client_search_routes,
    debug_routes,
)
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from backend.api import test_orm_api
from backend.services.db.configdb import db_engine

load_dotenv()

DEBUG_MODE = True

app = FastAPI(
    title="B2B Meeting Assistant API",
    description="API for B2B Meeting Assistant",
    version="1.0.0",
    debug=DEBUG_MODE,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include all routers with appropriate prefixes and tags
app.include_router(cache_routes.router, prefix="/api", tags=["Cache Management"])
app.include_router(client_search_routes.router, prefix="/api", tags=["Client Search"])
app.include_router(client_interne_data_routes.router, prefix="/api", tags=["Client Internal Data"])
app.include_router(client_externe_data_routes.router, prefix="/api", tags=["Client External Data"])

# Include debug routes only in DEBUG_MODE
if DEBUG_MODE:
    app.include_router(debug_routes.router, prefix="/api", tags=["Debug"])


@app.on_event("startup")
async def startup_event():
    """Initialize database on startup."""
    try:
        logger.info("Creating database tables...")
        db_engine.create_database()
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Failed to create database tables: {e}")
        raise


app.include_router(test_orm_api.router, prefix="/api/orm", tags=["ORM Test"])


@app.get("/")
async def root():
    """Return a welcome message for the API."""
    return {"message": "B2B Meeting Assistant API"}


@app.get("/health")
async def health_check():
    """Check the health status of the API."""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)  # nosec B104
