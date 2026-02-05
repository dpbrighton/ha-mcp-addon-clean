from fastapi import FastAPI, HTTPException
import os
import requests

app = FastAPI(title="Home Assistant MCP Server")

HA_URL = "http://homeassistant:8123/api"


def get_headers():
    token = os.environ.get("HA_TOKEN")
    if not token:
        raise HTTPException(
            status_code=500,
            detail="HA_TOKEN not set in add-on configuration",
        )
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }


@app.get("/api/overview")
def overview():
    try:
        resp = requests.get(
            f"{HA_URL}/config",
            headers=get_headers(),
            timeout=5,
        )
        resp.raise_for_status()
        config = resp.json()
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=str(e))

    return {
        "home_assistant": {
            "version": config.get("version"),
            "installation_type": config.get("installation_type"),
            "location_name": config.get("location_name"),
            "time_zone": config.get("time_zone"),
            "unit_system": config.get("unit_system"),
        },
        "counts": {},
    }
