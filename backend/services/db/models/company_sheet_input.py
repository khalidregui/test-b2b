from datetime import date
from typing import ClassVar, Optional

from pydantic import BaseModel, Field


class CompanySheetInput(BaseModel):
    """Schema pour recevoir les données d'entrée d'une fiche entreprise."""

    # --- Identity card ---
    company_identifier: Optional[str] = Field(
        None, description="Business identifier (SIRET, client code, etc.)"
    )
    company_name: str = Field(..., description="Company name", min_length=1)
    business_sector: Optional[str] = Field(None, description="Sector of business")
    address: Optional[str] = Field(None, description="Main address of the company")
    additional_addresses: Optional[str] = Field(None, description="Additional addresses")
    director_name: Optional[str] = Field(None, description="Name of the company director")
    workforce_size: Optional[str] = Field(None, description="Approximate number of employees")
    website_link: Optional[str] = Field(None, description="Company Website link")
    linkedin_link: Optional[str] = Field(None, description="Company LinkedIn link")

    # --- Contact ---
    contact_name: Optional[str] = Field(None, description="Full name of the contact person")
    contact_phone: Optional[str] = Field(None, description="Contact telephone number")
    contact_email: Optional[str] = Field(None, description="Email address of the contact person")

    # --- Business Data ---
    partnership_start_date: Optional[date] = Field(None, description="Start date of partnership")
    partnership_description: Optional[str] = Field(
        None, description="Partnership scope description"
    )

    # --- Statement of claims ---
    account_status: Optional[str] = Field(None, description="Payment or account status")
    outstanding_amount: Optional[float] = Field(None, ge=0, description="Outstanding debt amount")
    average_receivables_age: Optional[float] = Field(
        None, ge=0, description="Average age of receivables in days"
    )
    risk_level: Optional[str] = Field(None, description="Risk level of the client")

    # --- Complaints ---
    registered_complaints: Optional[str] = Field(None, description="Summary of complaints")

    # --- News ---
    company_news: Optional[str] = Field(None, description="Recent news about the client")
    sector_context: Optional[str] = Field(None, description="Sectoral context")
    cybersecurity_focus: Optional[str] = Field(None, description="Cybersecurity information")

    # --- Services ---
    service_offerings: Optional[str] = Field(None, description="Service offerings details")
    recommendations: Optional[str] = Field(None, description="Recommended services")

    class Config:
        """Pydantic model configuration."""

        json_schema_extra: ClassVar[dict] = {
            "example": {
                "company_name": "TechCorp Solutions",
                "business_sector": "Technology",
                "address": "123 Tech Street, Paris",
                "director_name": "John Doe",
                "contact_email": "contact@techcorp.com",
                "contact_phone": "+33 1 23 45 67 89",
                "workforce_size": "50-100",
                "website_link": "https://techcorp.com",
                "partnership_description": "Cybersecurity consulting services",
            }
        }
