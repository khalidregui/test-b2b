# Standard library helpers for scoped session management and typing
from contextlib import contextmanager
from typing import Any, Dict, Iterator, List, Optional

# Structured logging for observability across DB interactions
from loguru import logger

# SQLAlchemy core imports for ORM model definitions and engine/session plumbing
from sqlalchemy import Column, Date, DateTime, Float, Integer, String, Text, create_engine, func
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, declarative_base, sessionmaker

# Declarative base used to register ORM table mappings
Base = declarative_base()


# ORM model representing a B2B client entry persisted in company_sheet table
class CompanySheetORM(Base):
    """ORM Model representing a B2B company sheet record."""

    __tablename__ = "company_sheet"

    # client id
    id = Column(
        Integer, primary_key=True, autoincrement=True, comment="Unique identifier for each client"
    )
    created_at = Column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        comment="Timestamp when the company sheet was created",
    )

    company_identifier = Column(
        String(50),
        unique=True,
        nullable=True,
        comment="Business identifier (SIRET, client code, etc.)",
    )
    # --- Identity card ---
    company_name = Column(String(255), nullable=False, comment="Company name")
    business_sector = Column(String(255), nullable=True, comment="Sector of business")
    address = Column(Text, nullable=True, comment="Main address of the company")
    additional_addresses = Column(Text, nullable=True, comment="Additional addresses")
    director_name = Column(String(255), nullable=True, comment="Name of the company director")
    workforce_size = Column(
        String(50), nullable=True, comment="Approximate number of employees (e.g., 500-1000)"
    )
    website_link = Column(Text, nullable=True, comment="Company Website link")
    linkedin_link = Column(Text, nullable=True, comment="Company LinkedIn link")

    # --- Contact  ---
    contact_name = Column(String(255), nullable=True, comment="Full name of the contact person")
    contact_phone = Column(String(50), nullable=True, comment="Contact telephone number")
    contact_email = Column(
        String(255), nullable=True, comment="Email address of the contact person"
    )

    # --- Business Data ---
    partnership_start_date = Column(
        Date, nullable=True, comment="Start date of partnership with the client"
    )
    partnership_description = Column(
        Text, nullable=True, comment="Brief description of the partnership scope"
    )

    # --- statement of claims ---
    account_status = Column(
        String(50), nullable=True, comment="Payment or account status (e.g., 'A jour', 'En retard')"
    )
    outstanding_amount = Column(Float, nullable=True, comment="Outstanding debt amount (if any)")
    average_receivables_age = Column(
        Float, nullable=True, comment="Average age of receivables (in days)"
    )
    risk_level = Column(
        String(50), nullable=True, comment="Risk level of the client (e.g., 'Faible', 'Élevé')"
    )

    # --- complaints registered ---
    registered_complaints = Column(
        Text, nullable=True, comment="Summary about the complaints registered"
    )

    # --- actualites ---
    company_news = Column(Text, nullable=True, comment="Recent news or updates about the client")
    sector_context = Column(Text, nullable=True, comment="Sectoral context or industry insights")
    cybersecurity_focus = Column(
        Text, nullable=True, comment="Information related to cybersecurity trends"
    )

    # --- offres and services ---
    service_offerings = Column(
        Text, nullable=True, comment="Details about subscribed or proposed offers/services"
    )

    # -- recommendation --
    recommendations = Column(Text, nullable=True, comment="Recommended offers/services")


# Lightweight data-access layer encapsulating engine creation and CRUD helpers
class DatabaseEngine:
    """Wrapper class around SQLAlchemy for database management.

    Provides methods for connecting, creating tables, and managing sessions.
    """

    def __init__(self, db_url: str = "sqlite:///fiche_clients.db"):
        """Initialize the DatabaseEngine with a given database URL.

        :param db_url: SQLAlchemy-compatible database URL
                       Example: 'sqlite:///fiche_clients.db'
                                'postgresql://user:pass@host:port/dbname'
        """
        self.db_url = db_url

        # Instantiate SQLAlchemy engine once per application lifecycle
        self.engine = create_engine(self.db_url, echo=False, future=True)

        # Session factory with safer defaults for API-style usage
        self.Session = sessionmaker(
            bind=self.engine,
            autoflush=False,
            expire_on_commit=False,
            future=True,
        )

    @contextmanager
    def session_scope(self, commit_on_exit: bool = False) -> Iterator[Session]:
        """Provide a transactional scope around a series of operations."""
        # Lazily create a new session for the scope
        session: Session = self.Session()
        try:
            yield session
            if commit_on_exit:
                # Explicit commit allows caller to opt into transactional writes
                session.commit()
        except SQLAlchemyError:
            session.rollback()
            raise
        finally:
            session.close()

    def create_database(self):
        """Create all tables defined in the ORM models."""
        try:
            # Ensure database schema is materialized before any read/write
            Base.metadata.create_all(self.engine)
        except SQLAlchemyError:
            logger.exception("Error while ensuring database schema")
            raise
        logger.info("Database schema ensured for URL: {db_url}", db_url=self.db_url)

    def get_session(self) -> Session:
        """Create and return a new database session."""
        # Expose raw session factory for advanced consumers
        return self.Session()

    def insert_record(self, record: Base) -> Optional[Base]:
        """Insert a new ORM record into the database.

        :param record: Instance of a SQLAlchemy ORM model (CompanySheetORM).
        """
        try:
            # Use scoped session to make sure resources are cleaned up automatically
            with self.session_scope(commit_on_exit=True) as session:
                session.add(record)
        except SQLAlchemyError:
            logger.exception("Error inserting record")
            return None

        logger.success("Record inserted successfully (ID: {record_id})", record_id=record.id)
        return record

    def fetch_all_company_sheets(self) -> List[CompanySheetORM]:
        """Retrieve all company sheet records from the database.

        :return: List of CompanySheetORM objects.
        """
        try:
            # Read-only operations avoid auto-commit for predictable behavior
            with self.session_scope() as session:
                return session.query(CompanySheetORM).all()
        except SQLAlchemyError:
            logger.exception("Error fetching company sheet records")
            return []

    def fetch_company_sheet_by_id(self, sheet_id: int) -> Optional[CompanySheetORM]:
        """Retrieve a single company sheet by its identifier."""
        try:
            with self.session_scope() as session:
                return session.get(CompanySheetORM, sheet_id)
        except SQLAlchemyError:
            logger.exception("Error fetching company sheet with ID {sheet_id}", sheet_id=sheet_id)
            return None

    def update_company_sheet(
        self, sheet_id: int, updates: Dict[str, Any]
    ) -> Optional[CompanySheetORM]:
        """Update an existing company sheet with the provided values."""
        try:
            with self.session_scope(commit_on_exit=True) as session:
                company_sheet: Optional[CompanySheetORM] = session.get(CompanySheetORM, sheet_id)
                if company_sheet is None:
                    logger.warning("Company sheet with ID {sheet_id} not found", sheet_id=sheet_id)
                    return None

                for field_name, value in updates.items():
                    if hasattr(company_sheet, field_name):
                        setattr(company_sheet, field_name, value)
                    else:
                        logger.debug(
                            "Skipping unknown field {field_name} during update of ID {sheet_id}",
                            field_name=field_name,
                            sheet_id=sheet_id,
                        )

                session.add(company_sheet)
                return company_sheet
        except SQLAlchemyError:
            logger.exception("Error updating company sheet with ID {sheet_id}", sheet_id=sheet_id)
            return None
