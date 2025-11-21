import asyncio
import json
import os
import ast
from typing import Any, Dict, Optional

import pandas as pd
from fastapi import APIRouter, HTTPException, Query

from backend.services.rate_limiters.global_concurrency_limiter import global_concurrency_limiter
from backend.services.scrapping import pipeline
from backend.services.dataiku.pipeline_writer import send_scraped_data_to_dataiku
from backend.services.dataiku.readers import read_filtered_data
from backend.services.dataiku.pipeline_writer import send_conversation_to_dataiku
from backend.services.dataiku.readers import read_description

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


def get_client_from_excel(client_id: str, identity_df, receivables_df):
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


async def fetch_first_linkedin_profile(
    company_name: str,
    city: str
) -> Dict[str, Any]:
    """Run the scraping pipeline and return the profile_data of the first LinkedIn event."""
    print(f"🔍 DATAIKU PIPELINE: Starting pipeline for company: '{company_name}', city: '{city}'")
    
    try:
        # Exécuter le pipeline de scrapping
        pipeline_results = await pipeline.run_pipeline(
            company_name=company_name,
            city=city
        )
        
        print(f"🔍 DATAIKU PIPELINE: Pipeline results obtained: {type(pipeline_results)}")
        
        # Envoyer les données à Dataiku
        send_scraped_data_to_dataiku(pipeline_results)
        print("✅ DATAIKU PIPELINE: Data sent to Dataiku successfully")
        
        # Lire les données filtrées depuis Dataiku
        df_results = read_filtered_data()
        print(f"🔍 DATAIKU PIPELINE: Retrieved {len(df_results)} filtered results")
        
        # Extraire les summaries et profile_data
        summaries = ast.literal_eval(df_results.loc[0, "summaries"])
        profile_data = ast.literal_eval(df_results.loc[0, "profile_data"])
        
        print(f"🔍 DATAIKU PIPELINE: Summaries keys: {list(summaries.keys())}")
        print(f"🔍 DATAIKU PIPELINE: Profile data keys: {list(profile_data.keys())}")
        
        # Formater les données de profil comme avant
        formatted_profile_data = {
            "employees": profile_data.get("companySize"),
            "linkedin_url": profile_data.get("companyUrl"),
            "website_url": profile_data.get("website"),
            "Address": profile_data.get("companyAddress"),
            "activity": profile_data.get("industry"),
        }
        
        print(f"✅ DATAIKU PIPELINE: Successfully processed profile data: {formatted_profile_data}")
        
        return summaries, formatted_profile_data
        
    except Exception as e:
        print(f"❌ DATAIKU PIPELINE: Error in pipeline: {e}")
        import traceback
        traceback.print_exc()
        
        # Retourner des données par défaut en cas d'erreur
        return {}, {
            "employees": "Données indisponibles",
            "linkedin_url": "Données indisponibles",
            "website_url": "Données indisponibles",
            "Address": "Données indisponibles",
            "activity": "Données indisponibles",
        }

def generate_conversation(conversation : str) -> str:
    try :
        send_conversation_to_dataiku(conversation)
        result = read_description()
    except: 
        result = "Dataiku can not resume your text"
    return result

@router.get("/clients/{client_id:path}/scrapping_and_llm")
async def get_client_scraping_llm(
    client_id: str,
    _country: Optional[str] = Query(None, description="Country code"),
    fetch_linkedin: bool = Query(True, description="Fetch fresh LinkedIn data"),
) -> Dict[str, Any]:
    """Get client scraping and LLM data."""
    try:
        async with global_concurrency_limiter.acquire("scrapping_and_llm"):
            identity_df, receivables_df = load_excel_data()

            if not identity_df.empty:
                identity_row, _ = get_client_from_excel(client_id, identity_df, receivables_df)

                if identity_row is not None:
                    company_name = safe_get(identity_row, "RAISON_SOCIALE")
                    activity = safe_get(identity_row, "SECTEUR_ACTIVITE")

                    result = {
                        "identity_enrichment": {
                            "employees": "Données indisponibles",
                            "linkedin_url": "Données indisponibles",
                            "website_url": "Données indisponibles",
                            "address": "Données indisponibles",
                            "activity_linkedin": "Données indisponibles",
                        },
                        "news": {
                            "sector_context": [f"Évolution du secteur {activity}"],
                            "cybersecurity_focus": ["Renforcement de la sécurité"],
                            "company_news": [f"Actualités de {company_name}"],
                        },
                        "potential": {
                            "ongoing_acquisitions": ["Projects en cours d'évaluation"],
                            "upsell_cross_sell": ["Opportunités commerciales à identifier"],
                        },
                    }

                    if fetch_linkedin and company_name != "Données indisponibles":
                        try:
                            # ✅ NOUVELLE INTÉGRATION DATAIKU
                            summaries, profile_data = await fetch_first_linkedin_profile(
                                company_name=company_name,
                                city="Burkina faso"
                            )
                            
                            # Mettre à jour les données d'enrichissement d'identité
                            if profile_data:
                                if profile_data.get("employees"):
                                    result["identity_enrichment"]["employees"] = profile_data["employees"]
                                if profile_data.get("linkedin_url"):
                                    result["identity_enrichment"]["linkedin_url"] = profile_data["linkedin_url"]
                                if profile_data.get("website_url"):
                                    result["identity_enrichment"]["website_url"] = profile_data["website_url"]
                                if profile_data.get("Address"):
                                    result["identity_enrichment"]["address"] = profile_data["Address"]
                                if profile_data.get("activity"):
                                    result["identity_enrichment"]["activity_linkedin"] = profile_data["activity"]

                            # ✅ INTÉGRER LES SUMMARIES DATAIKU DANS LES NEWS
                            if summaries:
                                # Remplacer sector_context par "Sectorial context rss"
                                if summaries.get("Sectorial context rss"):
                                    result["news"]["sector_context"] = [summaries["Sectorial context rss"]]
                                
                                # Remplacer cybersecurity_focus par "cybersecurity context rss"
                                if summaries.get("cybersecurity context rss"):
                                    result["news"]["cybersecurity_focus"] = [summaries["cybersecurity context rss"]]
                                
                                # Remplacer company_news par "linkedin"
                                if summaries.get("linkedin"):
                                    result["news"]["company_news"] = [summaries["linkedin"]]

                            # Logique d'analyse des employés (conservée)
                            if (
                                profile_data.get("employees")
                                and profile_data["employees"] != "Données indisponibles"
                            ):
                                try:
                                    emp_str = str(profile_data["employees"])
                                    if "-" in emp_str:
                                        emp_count = int(emp_str.split("-")[0])
                                    elif "+" in emp_str:
                                        emp_count = int(emp_str.replace("+", ""))
                                    else:
                                        emp_count = int(emp_str)

                                    if emp_count > 500:
                                        result["potential"]["upsell_cross_sell"].append(
                                            "Grande entreprise - Potential très élevé"
                                        )
                                    elif emp_count > 100:
                                        result["potential"]["upsell_cross_sell"].append(
                                            "Entreprise importante - Potential élevé"
                                        )
                                    elif emp_count > 50:
                                        result["potential"]["upsell_cross_sell"].append(
                                            "Entreprise moyenne - Opportunités"
                                        )
                                    else:
                                        result["potential"]["upsell_cross_sell"].append(
                                            "PME - Solutions adaptées aux petites structures"
                                        )

                                except (ValueError, AttributeError):
                                    result["potential"]["upsell_cross_sell"].append(
                                        "Données employés LinkedIn - Analyse recommandée"
                                    )

                            if (
                                profile_data.get("linkedin_url")
                                and profile_data["linkedin_url"] != "Données indisponibles"
                            ):
                                result["potential"]["ongoing_acquisitions"].append(
                                    "Entreprise active - Potential de digitalisation élevé"
                                )

                        except Exception as e:
                            print(f"Error fetching LinkedIn/Dataiku data: {e}")
                            result["news"]["company_news"].append(
                                "Enrichissement LinkedIn/Dataiku temporairement indisponible"
                            )

                    return result

            if client_id in fake_data:
                client_data = fake_data[client_id]
                client_country = client_data["identity"].get("country")

                if _country and client_country != _country:
                    raise HTTPException(
                        status_code=404, detail="Client not found in specified country"
                    )

                return client_data["scraping_llm"]

            raise HTTPException(status_code=404, detail="Scraping/LLM data not found")

    except asyncio.TimeoutError:
        raise HTTPException(status_code=429, detail="Server is busy, please try again later.")


@router.get("/clients/{client_id}/partnership/update-description")
async def update_partnership_description(
    client_id: str,
    description: str = Query(..., description="Nouvelle description de partenariat")
) -> dict:
    """
    Route GET simple qui reçoit la description de partenariat et la retourne telle quelle.
    
    Args:
        client_id: Identifiant du client
        description: Nouvelle description de partenariat (via query parameter)
        
    Returns:
        dict: Description retournée telle quelle
    """
    try:
        print(f"📝 PARTNERSHIP: Mise à jour description pour client {client_id}")
        print(f"📝 PARTNERSHIP: Description reçue: {description[:100]}...")
        
        return {
            "success": True,
            "client_id": client_id,
            "description": generate_conversation(description),
            "message": "Description mise à jour avec succès"
        }
        
    except Exception as e:
        print(f"❌ PARTNERSHIP: Erreur lors de la mise à jour: {e}")
        raise HTTPException(
            status_code=500, 
            detail=f"Erreur lors de la mise à jour: {str(e)}"
        )
