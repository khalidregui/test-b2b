import json
from typing import Any, Dict, List, Optional

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


def get_client_from_excel(client_id: str, identity_df: pd.DataFrame, receivables_df: pd.DataFrame):
    """Get client data from Excel files using CODE_CLIENT."""
    identity_row = None
    receivables_row = None

    if not identity_df.empty:
        identity_row = identity_df[identity_df["CODE_CLIENT"].astype(str) == client_id]

        if identity_row.empty:
            try:
                client_id_float = float(client_id)
                identity_row = identity_df[identity_df["CODE_CLIENT"] == client_id_float]
            except ValueError:
                pass

    if not receivables_df.empty:
        receivables_row = receivables_df[receivables_df["CODE_CLIENT"].astype(str) == client_id]
        if receivables_row.empty:
            try:
                client_id_float = float(client_id)
                receivables_row = receivables_df[receivables_df["CODE_CLIENT"] == client_id_float]
            except ValueError:
                pass

    identity_result = (
        identity_row.iloc[0] if identity_row is not None and not identity_row.empty else None
    )
    receivables_result = (
        receivables_row.iloc[0]
        if receivables_row is not None and not receivables_row.empty
        else None
    )

    return identity_result, receivables_result


@router.get("/clients/{client_id:path}/identity")
async def get_client_identity(
    client_id: str, _country: Optional[str] = Query(None, description="Country code")
) -> Dict[str, Any]:
    """Get client identity data using CODE_CLIENT."""
    print(f"DEBUG: Received client_id: {client_id}")

    identity_df, receivables_df = load_excel_data()

    if not identity_df.empty:
        identity_row, _ = get_client_from_excel(client_id, identity_df, receivables_df)

        if identity_row is not None:
            company_name = safe_get(identity_row, "RAISON_SOCIALE")
            activity = safe_get(identity_row, "SECTEUR_ACTIVITE")

            nom = safe_get(identity_row, "NOM_PREMIER_RESPO", "")
            prenom = safe_get(identity_row, "PRENOM_PREMIER_RESPO", "")

            if nom != "Données indisponibles" and prenom != "Données indisponibles":
                ceo = f"{prenom} {nom}".strip()
            elif nom != "Données indisponibles":
                ceo = nom
            elif prenom != "Données indisponibles":
                ceo = prenom
            else:
                ceo = "Données indisponibles"

            return {
                "company_name": company_name,
                "ceo": ceo,
                "activity": activity,
                "other_addresses": "Données indisponibles",
                "country": _country or "BF",
            }

    if client_id in fake_data:
        client_data = fake_data[client_id]
        client_country = client_data["identity"].get("country")

        if _country and client_country != _country:
            raise HTTPException(status_code=404, detail="Client not found in specified country")

        return client_data["identity"]

    raise HTTPException(status_code=404, detail="Client not found")


@router.get("/clients/{client_id:path}/contact")
async def get_client_contact(
    client_id: str, _country: Optional[str] = Query(None, description="Country code")
) -> Dict[str, Any]:
    """Get client contact data using CODE_CLIENT."""
    identity_df, receivables_df = load_excel_data()

    if not identity_df.empty:
        identity_row, _ = get_client_from_excel(client_id, identity_df, receivables_df)

        if identity_row is not None:
            nom = safe_get(identity_row, "NOM_PREMIER_RESPO", "")
            prenom = safe_get(identity_row, "PRENOM_PREMIER_RESPO", "")

            if nom != "Données indisponibles" and prenom != "Données indisponibles":
                name = f"{prenom} {nom}".strip()
            elif nom != "Données indisponibles":
                name = nom
            elif prenom != "Données indisponibles":
                name = prenom
            else:
                name = "Données indisponibles"

            email = safe_get(identity_row, "EMAIL")
            phone = safe_get(identity_row, "NUMERO_TEL_ENTREPRISE")

            return {"name": name, "phone": phone, "email": email}

    return {
        "name": "Données indisponibles",
        "phone": "Données indisponibles",
        "email": "Données indisponibles",
    }


@router.get("/clients/{client_id:path}/receivables")
async def get_client_receivables(
    client_id: str, _country: Optional[str] = Query(None, description="Country code")
) -> Dict[str, Any]:
    """Get client receivables data using CODE_CLIENT."""
    identity_df, receivables_df = load_excel_data()

    if not receivables_df.empty:
        _, receivables_row = get_client_from_excel(client_id, identity_df, receivables_df)

        if receivables_row is not None:
            status = safe_get(receivables_row, "STATUT_CREANCE", "Données indisponibles")

            try:
                amount = float(safe_get(receivables_row, "MONTANT_CREANCE", 0))
            except (ValueError, TypeError):
                amount = 0

            try:
                average_age = float(safe_get(receivables_row, "ANCIENNETE_MOYENNE", 0))
            except (ValueError, TypeError):
                average_age = 0

            if status.lower() == "a jour" or status.lower() == "à jour":
                risk_level = "Risque Faible"
            elif amount > 1000000:
                risk_level = "Risque Élevé"
            elif amount > 500000:
                risk_level = "Risque Moyen"
            else:
                risk_level = "Risque Faible"

            return {
                "status": status,
                "amount": amount,
                "average_age": average_age,
                "risk_level": risk_level,
                "total_amount": amount,
            }

    return {
        "status": "Données indisponibles",
        "amount": "Données indisponibles",
        "average_age": "Données indisponibles",
        "risk_level": "Données indisponibles",
        "total_amount": "Données indisponibles",
    }


@router.get("/clients/{client_id:path}/partnership")
async def get_client_partnership(
    client_id: str, _country: Optional[str] = Query(None, description="Country code")
) -> Dict[str, Any]:
    """Get client partnership data."""
    identity_df, receivables_df = load_excel_data()

    if not identity_df.empty:
        identity_row, _ = get_client_from_excel(client_id, identity_df, receivables_df)

        if identity_row is not None:
            company_name = safe_get(identity_row, "RAISON_SOCIALE")
            return {
                "start_date": 2020,
                "description": f"Partenariat stratégique avec {company_name}",
                "points": ["Solutions de connectivité", "Services numériques", "Support technique"],
            }

    if client_id in fake_data:
        client_data = fake_data[client_id]
        client_country = client_data["identity"].get("country")

        if _country and client_country != _country:
            raise HTTPException(status_code=404, detail="Client not found in specified country")

        return client_data["partnership"]

    raise HTTPException(status_code=404, detail="Partnership data not found")


@router.get("/clients/{client_id:path}/revenues")
async def get_client_revenues(
    client_id: str,
    period: str = Query("monthly", description="Period: monthly, weekly, daily"),
    products: Optional[str] = Query(None, description="Comma-separated product list"),
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    _country: Optional[str] = Query(None, description="Country code"),
) -> List[Dict[str, Any]]:
    """Get client revenue data with filters."""
    identity_df, receivables_df = load_excel_data()

    if not identity_df.empty:
        identity_row, _ = get_client_from_excel(client_id, identity_df, receivables_df)

        if identity_row is not None:
            return []

    if client_id in fake_data:
        client_data = fake_data[client_id]
        client_country = client_data["identity"].get("country")

        if _country and client_country != _country:
            return []

        revenues = client_data["revenues"]
        results = []

        for revenue in revenues:
            revenue_obj = {
                "date": revenue["date"],
                "product": revenue["product"],
                "amount": revenue["amount"],
                "period": period,
            }

            if products:
                product_list = [p.strip() for p in products.split(",")]
                if revenue_obj["product"] not in product_list:
                    continue

            if start_date and revenue_obj["date"] < start_date:
                continue

            if end_date and revenue_obj["date"] > end_date:
                continue

            results.append(revenue_obj)

        return results

    return []


@router.get("/clients/{client_id:path}/complaints")
async def get_client_complaints(
    client_id: str,
    product: Optional[str] = Query(None, description="Product filter"),
    complaint_type: Optional[str] = Query(None, description="Complaint type filter"),
    _country: Optional[str] = Query(None, description="Country code"),
) -> List[Dict[str, Any]]:
    """Get client complaints data with filters."""
    identity_df, receivables_df = load_excel_data()

    if not identity_df.empty:
        identity_row, _ = get_client_from_excel(client_id, identity_df, receivables_df)

        if identity_row is not None:
            return [
                {
                    "title": "Aucune réclamation récente",
                    "description": "Le client n'a pas de réclamations en cours.",
                    "resolution": "Données indisponibles",
                    "product": "Données indisponibles",
                    "type": "Données indisponibles",
                }
            ]

    if client_id in fake_data:
        client_data = fake_data[client_id]
        client_country = client_data["identity"].get("country")

        if _country and client_country != _country:
            return []

        complaints = client_data["complaints"]
        results = []

        for complaint in complaints:
            if product and complaint.get("product") != product:
                continue
            if complaint_type and complaint.get("type") != complaint_type:
                continue
            results.append(complaint)

        return results

    return []


@router.get("/clients/{client_id:path}/services")
async def get_client_services(
    client_id: str, _country: Optional[str] = Query(None, description="Country code")
) -> List[Dict[str, Any]]:
    """Get client services data."""
    identity_df, receivables_df = load_excel_data()

    if not identity_df.empty:
        identity_row, _ = get_client_from_excel(client_id, identity_df, receivables_df)

        if identity_row is not None:
            return [
                {
                    "service_name": "Services Orange Business",
                    "category": "internet",
                    "status": "Actif",
                }
            ]

    if client_id in fake_data:
        client_data = fake_data[client_id]
        client_country = client_data["identity"].get("country")

        if _country and client_country != _country:
            return []

        return client_data["services"]

    return []
