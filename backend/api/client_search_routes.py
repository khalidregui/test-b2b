import json
from typing import Dict, List, Optional

import pandas as pd
from fastapi import APIRouter, HTTPException, Query

from .cache_routes import load_excel_data

router = APIRouter()

fake_data = {}
try:
    with open("fake_data.json", "r", encoding="utf-8") as f:
        fake_data = json.load(f)
except FileNotFoundError:
    print("Warning: fake_data.json not found, using Excel data only")


def safe_get(row, column, default="Données indisponibles"):
    """Safely get value from pandas row, return default if NaN or missing."""
    if row is None:
        return default
    try:
        value = row[column]
        if pd.isna(value) or value == "" or str(value).strip() == "":
            return default
        return str(value).strip()
    except (KeyError, IndexError):
        return default


@router.get("/clients/autocomplete")
async def autocomplete_clients(
    q: str = Query(..., description="Search query"),
    country: Optional[str] = Query(None, description="Country code"),
) -> List[Dict[str, str]]:
    """Autocomplete search for clients by CODE_CLIENT or company name."""
    identity_df, _ = load_excel_data()
    results = []
    query_lower = q.lower()

    identifiers = []
    company_names = []

    if not identity_df.empty:
        for _, row in identity_df.iterrows():
            client_id = str(row["CODE_CLIENT"])
            company_name = safe_get(row, "RAISON_SOCIALE", "Société inconnue")

            if client_id.startswith(q):
                identifiers.append(
                    {
                        "value": client_id,
                        "label": f"{client_id} - {company_name}",
                        "type": "identifier",
                    }
                )
            elif company_name.lower().startswith(query_lower):
                company_names.append(
                    {
                        "value": company_name,
                        "label": f"{company_name} ({client_id})",
                        "type": "company_name",
                    }
                )

    if not identifiers and not company_names and fake_data:
        for client_id, data in fake_data.items():
            client_country = data["identity"].get("country")
            if country and client_country != country:
                continue

            company_name = data["identity"]["company_name"]

            if client_id.lower().startswith(query_lower):
                identifiers.append(
                    {
                        "value": client_id,
                        "label": f"{client_id} - {company_name}",
                        "type": "identifier",
                    }
                )
            elif company_name.lower().startswith(query_lower):
                company_names.append(
                    {
                        "value": company_name,
                        "label": f"{company_name} ({client_id})",
                        "type": "company_name",
                    }
                )

    results = identifiers + company_names
    return results[:10]


@router.get("/clients/search")
async def search_clients(
    identifier: Optional[str] = Query(None, description="Client identifier (CODE_CLIENT)"),
    company_name: Optional[str] = Query(None, description="Company name"),
    country: Optional[str] = Query(None, description="Country code"),
) -> List[Dict[str, str]]:
    """Search clients by CODE_CLIENT or company name."""
    if not identifier and not company_name:
        raise HTTPException(status_code=400, detail="At least one search parameter is required")

    identity_df, _ = load_excel_data()
    results = []

    if not identity_df.empty:
        for _, row in identity_df.iterrows():
            client_id = str(row["CODE_CLIENT"])
            client_company_name = safe_get(row, "RAISON_SOCIALE", "Société inconnue")
            activity = safe_get(row, "SECTEUR_ACTIVITE", "Données indisponibles")

            if identifier and identifier in client_id:
                results.append(
                    {
                        "client_id": client_id,
                        "identifier": client_id,
                        "company_name": client_company_name,
                        "activity": activity,
                    }
                )
            elif company_name and company_name.lower() in client_company_name.lower():
                already_added = any(r["client_id"] == client_id for r in results)
                if not already_added:
                    results.append(
                        {
                            "client_id": client_id,
                            "identifier": client_id,
                            "company_name": client_company_name,
                            "activity": activity,
                        }
                    )

    if not results and fake_data:
        for client_id, data in fake_data.items():
            client_country = data["identity"].get("country")
            if country and client_country != country:
                continue

            if identifier and identifier in client_id:
                results.append(
                    {
                        "client_id": client_id,
                        "identifier": client_id,
                        "company_name": data["identity"]["company_name"],
                        "activity": data["identity"]["activity"],
                    }
                )
            elif company_name and company_name.lower() in data["identity"]["company_name"].lower():
                already_added = any(r["client_id"] == client_id for r in results)
                if not already_added:
                    results.append(
                        {
                            "client_id": client_id,
                            "identifier": client_id,
                            "company_name": data["identity"]["company_name"],
                            "activity": data["identity"]["activity"],
                        }
                    )

    return results
