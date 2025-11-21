import os
from datetime import datetime
from typing import Any, Dict

from fastapi import APIRouter, Query

from .client_externe_data_routes import fetch_first_linkedin_profile

router = APIRouter()


@router.get("/debug/files")
async def debug_files() -> Dict[str, Any]:
    """Debug endpoint to check file system."""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(current_dir))

    result = {
        "current_file": __file__,
        "current_dir": current_dir,
        "project_root": project_root,
        "project_root_files": [],
        "config_dir_exists": False,
        "config_dir_files": [],
        "config_file_exists": False,
    }

    try:
        if os.path.exists(project_root):
            result["project_root_files"] = os.listdir(project_root)

        config_dir = os.path.join(project_root, "config")
        result["config_dir_exists"] = os.path.exists(config_dir)

        if result["config_dir_exists"]:
            result["config_dir_files"] = os.listdir(config_dir)

        config_file = os.path.join(project_root, "config", "config.yaml")
        result["config_file_exists"] = os.path.exists(config_file)
        result["config_file_path"] = config_file

    except Exception as e:
        result["error"] = str(e)

    return result


@router.get("/debug/linkedin")
async def debug_linkedin_scraping(
    company_name: str = Query(..., description="Company name to search"),
    city: str = Query("Ouagadougou", description="City for search"),
    fetch_posts: bool = Query(False, description="Fetch posts"),
    fetch_profile: bool = Query(True, description="Fetch profile"),
) -> Dict[str, Any]:
    """Debug endpoint to test LinkedIn scraping directly."""
    print(f"🚀 LINKEDIN DEBUG ENDPOINT: Called with company_name='{company_name}', city='{city}'")

    result = await fetch_first_linkedin_profile(
        company_name=company_name, city=city, fetch_posts=fetch_posts, fetch_profile=fetch_profile
    )

    return {
        "debug_info": {
            "company_name": company_name,
            "city": city,
            "fetch_posts": fetch_posts,
            "fetch_profile": fetch_profile,
            "timestamp": datetime.now().isoformat(),
        },
        "linkedin_result": result,
    }
