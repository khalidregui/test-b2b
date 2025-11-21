import threading
from datetime import datetime, timedelta
from typing import Any, Dict, Tuple

import pandas as pd
from fastapi import APIRouter

router = APIRouter()

_excel_cache = {
    "identity_df": None,
    "receivables_df": None,
    "last_loaded": None,
    "cache_duration": timedelta(minutes=30),
    "lock": threading.Lock(),
}


def load_excel_data() -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Load data from Excel files with caching."""
    with _excel_cache["lock"]:
        now = datetime.now()
        if (
            _excel_cache["last_loaded"] is not None
            and _excel_cache["identity_df"] is not None
            and _excel_cache["receivables_df"] is not None
            and now - _excel_cache["last_loaded"] < _excel_cache["cache_duration"]
        ):
            print(f"DEBUG: Using cached Excel data (loaded at {_excel_cache['last_loaded']})")
            return _excel_cache["identity_df"], _excel_cache["receivables_df"]

        try:
            print("DEBUG: Loading Excel files from disk...")

            identity_df = pd.read_excel("/app/backend/Carte_Identite.xlsx")

            print(f"DEBUG: Identity DataFrame loaded with shape: {identity_df.shape}")
            print(f"DEBUG: Identity DataFrame columns: {list(identity_df.columns)}")

            receivables_df = pd.read_excel("/app/backend/Etat des crÇances.xlsx")
            print(f"DEBUG: Receivables DataFrame loaded with shape: {receivables_df.shape}")
            print(f"DEBUG: Receivables DataFrame columns: {list(receivables_df.columns)}")

            _excel_cache["identity_df"] = identity_df
            _excel_cache["receivables_df"] = receivables_df
            _excel_cache["last_loaded"] = now

            print(f"DEBUG: Excel data cached at {now}")
            return identity_df, receivables_df

        except Exception as e:
            print(f"Error loading Excel files: {e}")
            if (
                _excel_cache["identity_df"] is not None
                and _excel_cache["receivables_df"] is not None
            ):
                print("DEBUG: Using expired cache due to loading error")
                return _excel_cache["identity_df"], _excel_cache["receivables_df"]
            return pd.DataFrame(), pd.DataFrame()


def clear_excel_cache():
    """Clear the Excel cache manually."""
    with _excel_cache["lock"]:
        _excel_cache["identity_df"] = None
        _excel_cache["receivables_df"] = None
        _excel_cache["last_loaded"] = None
        print("DEBUG: Excel cache cleared")


def get_cache_info() -> Dict[str, Any]:
    """Get information about the current cache state."""
    with _excel_cache["lock"]:
        return {
            "is_cached": _excel_cache["identity_df"] is not None,
            "last_loaded": _excel_cache["last_loaded"].isoformat()
            if _excel_cache["last_loaded"]
            else None,
            "cache_duration_minutes": _excel_cache["cache_duration"].total_seconds() / 60,
            "identity_df_shape": _excel_cache["identity_df"].shape
            if _excel_cache["identity_df"] is not None
            else None,
            "receivables_df_shape": _excel_cache["receivables_df"].shape
            if _excel_cache["receivables_df"] is not None
            else None,
        }


@router.get("/cache/info")
async def get_cache_status() -> Dict[str, Any]:
    """Get current cache information."""
    return get_cache_info()


@router.post("/cache/clear")
async def clear_cache() -> Dict[str, str]:
    """Clear the Excel cache."""
    clear_excel_cache()
    return {"message": "Cache cleared successfully"}


@router.post("/cache/refresh")
async def refresh_cache() -> Dict[str, Any]:
    """Force refresh the Excel cache."""
    clear_excel_cache()
    identity_df, receivables_df = load_excel_data()
    return {"message": "Cache refreshed successfully", "cache_info": get_cache_info()}
