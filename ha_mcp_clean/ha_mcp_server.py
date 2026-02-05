from fastapi import FastAPI, HTTPException
import os
import requests

app = FastAPI(title="Home Assistant MCP Server")

# -------------------------------
# HELPER FUNCTION: Get current HA headers
# -------------------------------
def get_ha_headers():
    """
    Dynamically read HA_TOKEN from environment on each request.
    Trims whitespace to avoid common token issues.
    """
    token = os.environ.get("HA_TOKEN", "").strip()
    if not token:
        raise RuntimeError("HA_TOKEN not set or empty. Check add-on config.")
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

# -------------------------------
# HA CORE API URL
# -------------------------------
# Using core HA API for long-lived token compatibility
HA_URL = "http://homeassistant:8123/api"

# -------------------------------
# DIAGNOSTIC ENVIRONMENT LOGGING
# -------------------------------
print("=== MCP ENVIRONMENT DUMP ===", flush=True)
for key, value in os.environ.items():
    if "HA" in key or "TOKEN" in key:
        print(f"{key}='{value}'", flush=True)
print("=== END ENV DUMP ===", flush=True)

# -------------------------------
# HEALTH CHECK
# -------------------------------
@app.get("/")
def root():
    token_present = bool(os.environ.get("HA_TOKEN", "").strip())
    return {
        "status": "running",
        "ha_token_present": token_present
    }

# -------------------------------
# OVERVIEW ENDPOINT
# -------------------------------
@app.get("/api/overview")
def overview():
    """
    Fetch Home Assistant configuration and provide a summary.
    """
    try:
        headers = get_ha_headers()
        resp = requests.get(f"{HA_URL}/config", headers=headers, timeout=5)
        resp.raise_for_status()
        config = resp.json()
    except requests.RequestException as e:
        raise HTTPException(
            status_code=502,
            detail=f"Error contacting Home Assistant API: {e}"
        )
    except RuntimeError as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

    # Example structure — counts can be filled dynamically later
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
# TASKS ENDPOINT (stub)
# -------------------------------
@app.get("/api/tasks")
def tasks():
    """
    Stub endpoint for AI to retrieve or manage tasks.
    """
    return []

# -------------------------------
# DYNAMIC ENTITY / DASHBOARD ENDPOINTS (future)
# -------------------------------
# Example placeholders for AI-driven generation
# You can add endpoints here to create dashboards, automations, etc.
