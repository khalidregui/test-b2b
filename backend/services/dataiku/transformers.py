import json
from datetime import datetime
from typing import Any, Dict, List, Mapping, Sequence

import pandas as pd
from pydantic import BaseModel

DATAFRAME_COLUMNS = [
    "source",
    "source_type",
    "title",
    "text",
    "url",
    "published_at",
    "profile_data",
    "error",
]


def _event_to_row(source_name: str, event: Any) -> Dict[str, Any]:
    """Event to row."""
    if isinstance(event, BaseModel):
        data = event.model_dump()
    elif isinstance(event, Mapping):
        data = dict(event)
    else:
        data = {"text": str(event)}

    profile = data.get("profile_data")
    if isinstance(profile, dict):
        profile = json.dumps(profile)

    # Normalize published_at to ISO string (Dataiku handles strings / datetimes)
    published_at = data.get("published_at")
    if isinstance(published_at, (datetime,)):
        published_at = published_at.isoformat()

    return {
        "source": data.get("source") or source_name,
        "source_type": data.get("source_type"),
        "title": data.get("title"),
        "text": data.get("text"),
        "url": data.get("url"),
        "published_at": published_at,
        "profile_data": profile,
        "error": None,
    }


def pipeline_results_to_dataframe(results: Dict[str, Any]) -> pd.DataFrame:
    """Pipeline results to dataframe."""
    rows: List[Dict[str, Any]] = []

    for plugin_name, payload in results.items():
        # error object
        if isinstance(payload, Mapping) and "error" in payload:
            rows.append(
                {
                    "source": plugin_name,
                    "source_type": None,
                    "title": None,
                    "text": None,
                    "url": None,
                    "published_at": None,
                    "profile_data": None,
                    "error": payload.get("error"),
                }
            )
            continue

        # sequence of events
        if isinstance(payload, Sequence) and not isinstance(payload, (str, bytes, bytearray)):
            for event in payload:
                rows.append(_event_to_row(plugin_name, event))
            continue

        # single event
        if payload is not None:
            rows.append(_event_to_row(plugin_name, payload))

    if not rows:
        return pd.DataFrame(columns=DATAFRAME_COLUMNS)

    return pd.DataFrame(rows, columns=DATAFRAME_COLUMNS)
