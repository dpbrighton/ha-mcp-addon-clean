from fastapi import FastAPI, HTTPException
import os
import requests

app = FastAPI(title="Home Assistant MCP Server")

# -------------------------------
# Read long-lived token from environment
# -------------------------------
HA_TOKEN = os.environ.get("HA_TOKEN", "").strip()
if not HA_TOKEN:
    print("❌ ERROR: HA_TOKEN not set in environment", flush=True)

HEADERS = {
    "Authorization": f"Bearer {HA_TOKEN}" if HA_TOKEN else "",
    "Content-Type": "application/json",
}

# -------------------------------
# Use Core API (not Supervisor API)
# -------------------------------
HA_URL = "http://homeassistant:8123/api"

# -------------------------------
# Diagnostic environment dump
# -------------------------------
print("=== MCP ENVIRONMENT DUMP ===", flush=True)
for key, value in os.environ.items():
    if "HA" in key or "TOKEN" in key:
        print(f"{key}='{value}'", flush=True)
print("=== END ENV DUMP ===", flush=True)

# -------------------------------
# Health check
# -------------------------------
@app.get("/")
def root():
    return {
        "status": "running",
        "ha_token_present": bool(HA_TOKEN),
    }

# -------------------------------
# Overview endpoint
# -------------------------------
@app.get("/api/overview")
def overview():
    if not HA_TOKEN:
        raise HTTPException(
            status_code=500,
            detail="HA_TOKEN not set. Add-on configuration required."
        )
    try:
        resp = requests.get(f"{HA_URL}/config", headers=HEADERS, timeout=5)
        resp.raise_for_status()
        config = resp.json()
    except requests.RequestException as e:
        raise HTTPException(
            status_code=502,
            detail=f"Error contacting Home Assistant Core API: {e}"
        )

    return {
        "home_assistant": {
            "version": config.get("version"),
            "location_name": config.get("name"),
            "time_zone": config.get("time_zone"),
            "unit_system": config.get("unit_system"),
            "installation_type": "homeassistant_os",
        },
        "counts": {
            "areas": 0,
            "devices": 0,
            "entities": 0,
            "automations": 0,
            "scripts": 0,
            "dashboards": 0,
        },
    }

# -------------------------------
# Tasks endpoint (stub)
# -------------------------------
@app.get("/api/tasks")
def tasks():
    return []

# -------------------------------
# Future endpoints (dashboards, automations, etc.)
# -------------------------------
