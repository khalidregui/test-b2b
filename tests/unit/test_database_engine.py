"""Unit tests targeting DatabaseEngine failure modes and persistence guarantees."""

# Test framework and utilities
import pytest

# Subject under test and ORM model dependencies
from backend.services.db.database_engine import CompanySheetORM, DatabaseEngine


def _build_sqlite_url(tmp_path, filename):
    """Construct a SQLite URL for the temporary directory.

    Args:
        tmp_path (pathlib.Path): Pytest fixture that yields a temporary pathlib.Path.
        filename (str): Name of the SQLite database file to create under tmp_path.

    Returns:
        str: SQLAlchemy-compatible database URL using the temporary file.
    """
    # Convert the temporary path into a concrete SQLite URL the engine can consume.
    return f"sqlite:///{tmp_path / filename}"


def test_insert_record_persists_complex_payload(tmp_path):
    """Validate that insert_record persists a high-signal company sheet payload.

    Args:
        tmp_path (pathlib.Path): Temporary directory provided by the pytest fixture.
    """
    # Arrange - Build an isolated database to ensure test independence.
    db_url = _build_sqlite_url(tmp_path, "insert_success.db")
    engine = DatabaseEngine(db_url=db_url)
    engine.create_database()

    # Act - Insert a realistic company sheet mimicking production ingestion volume.
    payload = CompanySheetORM(
        company_name="Acme Defense Systems",
        business_sector="Aerospace and Defense",
        account_status="Past due",
        outstanding_amount=125000.50,
        risk_level="High",
        contact_email="contact@acme-defense.example",
    )
    inserted_record = engine.insert_record(payload)

    # Assert - Confirm the record is persisted and retrievable with a timestamp.
    assert inserted_record is not None, "insert_record should echo the ORM instance that was stored"
    assert inserted_record.id is not None, "Persisted record should receive a database-generated ID"
    assert inserted_record.created_at is not None, (
        "created_at should be auto-populated after insert"
    )
    stored_records = engine.fetch_all_company_sheets()
    assert len(stored_records) == 1, "Exactly one record should exist after insertion"
    assert stored_records[0].company_name == "Acme Defense Systems"
    assert stored_records[0].created_at is not None, "Reloaded record should retain its timestamp"


def test_session_scope_rolls_back_on_exception(tmp_path):
    """Ensure session_scope performs rollbacks when the work unit raises.

    Args:
        tmp_path (pathlib.Path): Temporary directory provided by the pytest fixture.
    """
    # Arrange - Create a dedicated database for this rollback scenario.
    db_url = _build_sqlite_url(tmp_path, "rollback.db")
    engine = DatabaseEngine(db_url=db_url)
    engine.create_database()

    # Act - Trigger a failure midway through a transactional scope to force rollback.
    with pytest.raises(RuntimeError):
        with engine.session_scope(commit_on_exit=True) as session:
            session.add(
                CompanySheetORM(
                    company_name="Globex Corporation",
                    account_status="Current",
                    risk_level="Moderate",
                )
            )
            raise RuntimeError("Simulated downstream failure during commit pipeline")

    # Assert - After rollback there should be no stray records in the database.
    persisted_records = engine.fetch_all_company_sheets()
    assert not persisted_records, "Rollback should ensure no records survive the failed transaction"


def test_insert_record_handles_integrity_error(tmp_path):
    """Validate insert_record surfaces insert failures without polluting the database.

    Args:
        tmp_path (pathlib.Path): Temporary directory provided by the pytest fixture.
    """
    # Arrange - Spin up an isolated database to capture integrity failures.
    db_url = _build_sqlite_url(tmp_path, "integrity_error.db")
    engine = DatabaseEngine(db_url=db_url)
    engine.create_database()

    # Act - Insert a payload that violates the NOT NULL constraint to mimic ETL bugs.
    bad_payload = CompanySheetORM(
        company_name=None,
        account_status="Past due",
    )
    result = engine.insert_record(bad_payload)

    # Assert - Database should stay empty and the method should signal the failure.
    assert result is None, "Failed insertions should return None to signal the error to callers"
    assert not engine.fetch_all_company_sheets(), "Database should remain empty after failed insert"


def test_update_company_sheet_applies_partial_mutations(tmp_path):
    """Assert update_company_sheet persists targeted field changes atomically.

    Args:
        tmp_path (pathlib.Path): Temporary directory provided by the pytest fixture.
    """
    # Arrange - Materialize a record that represents an onboarded company sheet.
    db_url = _build_sqlite_url(tmp_path, "update_sheet.db")
    engine = DatabaseEngine(db_url=db_url)
    engine.create_database()
    original = CompanySheetORM(
        company_name="Initech",
        business_sector="Software",
        account_status="Current",
        outstanding_amount=0.0,
        risk_level="Low",
    )
    inserted = engine.insert_record(original)
    assert inserted is not None, "Precondition failed: initial insert should succeed"

    # Act - Apply an update that mirrors a collections workflow escalation.
    updated = engine.update_company_sheet(
        sheet_id=inserted.id,
        updates={
            "account_status": "Delinquent",
            "outstanding_amount": 240000.75,
            "nonexistent_field": "ignored",
        },
    )

    # Assert - Only known fields should mutate and data should survive across sessions.
    assert updated is not None, "update_company_sheet should return the mutated ORM instance"
    assert updated.account_status == "Delinquent"
    assert updated.outstanding_amount == 240000.75
    reloaded = engine.fetch_company_sheet_by_id(inserted.id)
    assert reloaded is not None, "Reload should find the updated company sheet"
    assert reloaded.account_status == "Delinquent"
    assert reloaded.outstanding_amount == pytest.approx(240000.75)
    assert reloaded.risk_level == "Low", "Unchanged fields should be preserved"
