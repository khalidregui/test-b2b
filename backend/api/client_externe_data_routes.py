import asyncio
import json
import os
from typing import Any, Dict, Optional

import pandas as pd
from fastapi import APIRouter, HTTPException, Query

from backend.services.rate_limiters.global_concurrency_limiter import global_concurrency_limiter
from backend.services.scrapping import pipeline

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
    *,
    company_name: str,
    city: str,
    fetch_posts: bool = False,
    fetch_profile: bool = True,
    config_path: str = "/config/config.yaml",
) -> Dict[str, Any]:
    """Run the scraping pipeline and return the profile_data of the first LinkedIn event."""
    print(f"🔍 LINKEDIN DEBUG: Starting scraping for company: '{company_name}', city: '{city}'")
    print(
        f"🔍 LINKEDIN DEBUG: Parameters - fetch_posts: {fetch_posts}, "
        f"fetch_profile: {fetch_profile}"
    )
    print(f"🔍 LINKEDIN DEBUG: Config path: {config_path}")

    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(os.path.dirname(current_dir))

        clean_config_path = config_path.lstrip("./")
        absolute_config_path = os.path.join(project_root, clean_config_path)

        print(f"🔍 LINKEDIN DEBUG: Current file directory: {current_dir}")
        print(f"🔍 LINKEDIN DEBUG: Project root: {project_root}")
        print(f"🔍 LINKEDIN DEBUG: Clean config path: {clean_config_path}")
        print(f"🔍 LINKEDIN DEBUG: Absolute config path: {absolute_config_path}")

        if not os.path.exists(absolute_config_path):
            print(f"❌ LINKEDIN DEBUG: Config file not found at: {absolute_config_path}")
            return {"error": "Config file not found", "config_path": absolute_config_path}

        print("✅ LINKEDIN DEBUG: Config file found, calling pipeline.run_pipeline...")

        pipeline_results = await pipeline.run_pipeline(
            config_path=absolute_config_path,
            company_name=company_name,
            city=city,
            fetch_posts=fetch_posts,
            fetch_profile=fetch_profile,
        )

        print(f"🔍 LINKEDIN DEBUG: Pipeline results type: {type(pipeline_results)}")

        if isinstance(pipeline_results, dict):
            keys_info = list(pipeline_results.keys())
        else:
            keys_info = "Not a dict"
        print(f"🔍 LINKEDIN DEBUG: Pipeline results keys: {keys_info}")
        print(f"🔍 LINKEDIN DEBUG: Full pipeline results: {pipeline_results}")

        if not pipeline_results:
            print("❌ LINKEDIN DEBUG: Pipeline returned empty results")
            return {"error": "Pipeline returned empty results"}

        linkedin_results = pipeline_results.get("linkedin", [])
        print(f"🔍 LINKEDIN DEBUG: LinkedIn results count: {len(linkedin_results)}")
        print(f"🔍 LINKEDIN DEBUG: LinkedIn results: {linkedin_results}")

        if not linkedin_results:
            print("❌ LINKEDIN DEBUG: No LinkedIn results in pipeline")
            return {
                "error": "No LinkedIn results in pipeline",
                "pipeline_keys": list(pipeline_results.keys()),
            }

        first_event = linkedin_results[0]
        print(f"🔍 LINKEDIN DEBUG: First event type: {type(first_event)}")

        if hasattr(first_event, "__dict__"):
            attributes_info = dir(first_event)
        else:
            attributes_info = "No attributes"
        print(f"🔍 LINKEDIN DEBUG: First event attributes: {attributes_info}")

        if hasattr(first_event, "profile_data"):
            data = first_event.profile_data
            print(f"🔍 LINKEDIN DEBUG: Profile data found: {data}")
            print(f"🔍 LINKEDIN DEBUG: Profile data type: {type(data)}")

            profile_data = {
                "employees": data.get("companySize"),
                "linkedin_url": data.get("companyUrl"),
                "website_url": data.get("website"),
                "Address": data.get("companyAddress"),
                "activity": data.get("industry"),
            }
            print(f"✅ LINKEDIN DEBUG: Successfully processed profile data: {profile_data}")
            return profile_data

        print("❌ LINKEDIN DEBUG: First event has no profile_data attribute")

        if hasattr(first_event, "__dict__"):
            dict_keys = list(first_event.__dict__.keys())
        else:
            dict_keys = "None"
        print(f"🔍 LINKEDIN DEBUG: Available attributes: {dict_keys}")
        return {"error": "No profile_data attribute", "event_type": str(type(first_event))}

    except ImportError as e:
        print(f"❌ LINKEDIN DEBUG: Import error: {e}")
        return {"error": f"Import error: {e!s}"}
    except FileNotFoundError as e:
        print(f"❌ LINKEDIN DEBUG: File not found: {e}")
        return {"error": f"File not found: {e!s}"}
    except Exception as e:
        print(f"❌ LINKEDIN DEBUG: Unexpected error: {e}")
        import traceback

        traceback.print_exc()
        return {"error": f"Unexpected error: {e!s}", "traceback": traceback.format_exc()}


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
                        "partnership_summary": f"Partenariat stratégique avec {company_name} "
                        f"dans le secteur {activity}",
                        "news": {
                            "sector_context": [
                                f"Évolution du secteur {activity}",
                                "Transformation digitale en cours",
                            ],
                            "cybersecurity_focus": [
                                "Reinforcement de la sécurité",
                                "Mise à jour des systèmes",
                            ],
                            "company_news": [
                                f"Actualités de {company_name}",
                                "Développement des activités",
                            ],
                        },
                        "potential": {
                            "ongoing_acquisitions": ["Projects en cours d'évaluation"],
                            "upsell_cross_sell": ["Opportunités commerciales à identifier"],
                        },
                    }

                    if fetch_linkedin and company_name != "Données indisponibles":
                        try:
                            linkedin_data = await fetch_first_linkedin_profile(
                                company_name=company_name,
                                city="Burkina faso",
                                fetch_posts=False,
                                fetch_profile=True,
                            )

                            if linkedin_data:
                                if linkedin_data.get("employees"):
                                    result["identity_enrichment"]["employees"] = linkedin_data[
                                        "employees"
                                    ]
                                if linkedin_data.get("linkedin_url"):
                                    result["identity_enrichment"]["linkedin_url"] = linkedin_data[
                                        "linkedin_url"
                                    ]
                                if linkedin_data.get("website_url"):
                                    result["identity_enrichment"]["website_url"] = linkedin_data[
                                        "website_url"
                                    ]
                                if linkedin_data.get("Address"):
                                    result["identity_enrichment"]["address"] = linkedin_data[
                                        "Address"
                                    ]
                                if linkedin_data.get("activity"):
                                    result["identity_enrichment"]["activity_linkedin"] = (
                                        linkedin_data["activity"]
                                    )

                                if linkedin_data.get("activity"):
                                    result["news"]["company_news"].append(
                                        f"Secteur d'activité LinkedIn: {linkedin_data['activity']}"
                                    )
                                if (
                                    linkedin_data.get("website_url")
                                    and linkedin_data["website_url"] != "Données indisponibles"
                                ):
                                    result["news"]["company_news"].append(
                                        f"Site web identifié: {linkedin_data['website_url']}"
                                    )

                                if (
                                    linkedin_data.get("employees")
                                    and linkedin_data["employees"] != "Données indisponibles"
                                ):
                                    try:
                                        emp_str = str(linkedin_data["employees"])
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
                                    linkedin_data.get("linkedin_url")
                                    and linkedin_data["linkedin_url"] != "Données indisponibles"
                                ):
                                    result["potential"]["ongoing_acquisitions"].append(
                                        "Entreprise active - Potential de digitalisation élevé"
                                    )

                        except Exception as e:
                            print(f"Error fetching LinkedIn data: {e}")
                            result["news"]["company_news"].append(
                                "Enrichissement LinkedIn temporairement indisponible"
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
            "description": description,
            "message": "Description mise à jour avec succès"
        }
        
    except Exception as e:
        print(f"❌ PARTNERSHIP: Erreur lors de la mise à jour: {e}")
        raise HTTPException(
            status_code=500, 
            detail=f"Erreur lors de la mise à jour: {str(e)}"
        )