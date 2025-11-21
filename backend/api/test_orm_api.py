from typing import List

from fastapi import APIRouter, HTTPException, status
from loguru import logger

from backend.services.db.configdb import db_engine
from backend.services.db.database_engine import CompanySheetORM
from backend.services.db.models.company_sheet_input import CompanySheetInput

# Create router for ORM routes
router = APIRouter()


def orm_to_dict(orm_obj) -> dict:
    """Convert ORM object to dictionary with proper serialization."""
    result = {}
    for column in orm_obj.__table__.columns:
        value = getattr(orm_obj, column.name)
        if hasattr(value, "isoformat"):  # datetime, date
            result[column.name] = value.isoformat()
        else:
            result[column.name] = value
    return result


def find_company_by_identifier(company_identifier: str) -> CompanySheetORM:
    """Find company by identifier using existing DatabaseEngine methods."""
    with db_engine.session_scope() as session:
        return (
            session.query(CompanySheetORM)
            .filter(CompanySheetORM.company_identifier == company_identifier)
            .first()
        )


@router.post("/company-sheets", status_code=status.HTTP_201_CREATED)
async def create_company_sheet(company_data: CompanySheetInput) -> dict:
    """Create a new company sheet in the database.

    Args:
        company_data: Company sheet data from request body

    Returns:
        Created company sheet as dictionary with ID and timestamps

    Raises:
        HTTPException: If creation fails or company_identifier already exists
    """
    try:
        # Check if company_identifier already exists
        if company_data.company_identifier:
            existing_company = find_company_by_identifier(company_data.company_identifier)
            if existing_company:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        f"Company with identifier '{company_data.company_identifier}' "
                        "already exists"
                    ),
                )

        company_orm = CompanySheetORM()

        for key, value in company_data.model_dump(exclude_unset=True).items():
            if hasattr(company_orm, key):
                setattr(company_orm, key, value)
            else:
                logger.warning(f"Field '{key}' not found in CompanySheetORM")

        created_company = db_engine.insert_record(company_orm)

        if created_company is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create company sheet",
            )

        logger.info(
            f"Company sheet created successfully: {created_company.company_name} "
            f"(Identifier: {created_company.company_identifier})"
        )

        return orm_to_dict(created_company)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating company sheet: {e!s}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {e!s}",
        )


@router.get("/company-sheets", response_model=List[dict])
async def get_all_company_sheets() -> List[dict]:
    """Retrieve all company sheets from the database.

    Returns:
        List of all company sheets as dictionaries

    Raises:
        HTTPException: If retrieval fails
    """
    try:
        company_sheets = db_engine.fetch_all_company_sheets()

        logger.info(f"Retrieved {len(company_sheets)} company sheets")

        return [orm_to_dict(sheet) for sheet in company_sheets]

    except Exception as e:
        logger.error(f"Error retrieving company sheets: {e!s}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {e!s}",
        )


@router.get("/company-sheets/{company_identifier}")
async def get_company_sheet_by_identifier(company_identifier: str) -> dict:
    """Retrieve a specific company sheet by company identifier.

    Args:
        company_identifier: Company identifier to retrieve

    Returns:
        Company sheet data as dictionary

    Raises:
        HTTPException: If company not found or retrieval fails
    """
    try:
        company_sheet = find_company_by_identifier(company_identifier)

        if company_sheet is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Company sheet with identifier '{company_identifier}' not found",
            )

        logger.info(
            f"Retrieved company sheet: {company_sheet.company_name} "
            f"(Identifier: {company_identifier})"
        )

        return orm_to_dict(company_sheet)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving company sheet {company_identifier}: {e!s}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {e!s}",
        )


@router.put("/company-sheets/{company_identifier}")
async def update_company_sheet(company_identifier: str, company_data: CompanySheetInput) -> dict:
    """Update an existing company sheet by company identifier.

    Args:
        company_identifier: Company identifier to update
        company_data: Updated company sheet data

    Returns:
        Updated company sheet as dictionary

    Raises:
        HTTPException: If company not found or update fails
    """
    try:
        # Find the company by identifier
        company_sheet = find_company_by_identifier(company_identifier)
        if company_sheet is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Company sheet with identifier '{company_identifier}' not found",
            )

        updates = company_data.model_dump(exclude_unset=True)

        # If updating company_identifier, check it doesn't already exist
        if "company_identifier" in updates and updates["company_identifier"] != company_identifier:
            existing_with_new_id = find_company_by_identifier(updates["company_identifier"])
            if existing_with_new_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        f"Company with identifier '{updates['company_identifier']}' already exists"
                    ),
                )

        # Use existing update method with the technical ID
        updated_company = db_engine.update_company_sheet(company_sheet.id, updates)

        if updated_company is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Failed to update company sheet with identifier '{company_identifier}'",
            )

        logger.info(
            f"Company sheet updated successfully: {updated_company.company_name} "
            f"(Identifier: {company_identifier})"
        )

        return orm_to_dict(updated_company)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating company sheet {company_identifier}: {e!s}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {e!s}",
        )


@router.delete("/company-sheets/{company_identifier}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_company_sheet(company_identifier: str):
    """Delete a company sheet by company identifier.

    Args:
        company_identifier: Company identifier to delete

    Raises:
        HTTPException: If company not found or deletion fails
    """
    try:
        # Find the company by identifier
        company_sheet = find_company_by_identifier(company_identifier)

        if company_sheet is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Company sheet with identifier '{company_identifier}' not found",
            )

        # Delete using session directly since no delete method exists in DatabaseEngine
        with db_engine.session_scope(commit_on_exit=True) as session:
            # Re-query in this session to avoid detached instance
            company_to_delete = (
                session.query(CompanySheetORM)
                .filter(CompanySheetORM.company_identifier == company_identifier)
                .first()
            )

            if company_to_delete:
                session.delete(company_to_delete)
                logger.info(f"Company sheet {company_identifier} deleted successfully")
            else:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Company sheet with identifier '{company_identifier}' not found",
                )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting company sheet {company_identifier}: {e!s}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {e!s}",
        )


@router.get("/test-db-connection")
async def test_database_connection() -> dict:
    """Test database connection and return basic info.

    Returns:
        Database connection status and basic stats

    Raises:
        HTTPException: If connection fails
    """
    try:
        company_sheets = db_engine.fetch_all_company_sheets()

        return {
            "status": "connected",
            "database_url": db_engine.db_url.split("@")[-1],
            "total_company_sheets": len(company_sheets),
            "message": "Database connection successful",
        }

    except Exception as e:
        logger.error(f"Database connection test failed: {e!s}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database connection failed: {e!s}",
        )
