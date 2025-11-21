import os

from backend.services.db.database_engine import DatabaseEngine


def get_database_url() -> str:
    """Construct PostgreSQL URL from environment variables."""
    db_user = os.getenv("DB_USER", "postgres")
    db_password = os.getenv("DB_PASSWORD", "example")
    db_host = os.getenv("DB_HOST", "localhost")
    db_port = os.getenv("DB_PORT", "5432")
    db_name = os.getenv("DB_NAME", "b2b_meeting_assistant")

    return f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"


# Globale instance for database engine
db_engine = DatabaseEngine(get_database_url())
