from fastapi import FastAPI, HTTPException
import os
import requests

app = FastAPI(title="Home Assistant MCP Server")

# -------------------------------
# HELPER FUNCTION: Get Supervisor headers
# -------------------------------
def get_ha_headers():
    """
    Use SUPERVISOR_TOKEN provided automatically to all add-ons.
    This avoids long-lived tokens, secrets, and YAML issues.
    """
    token = os.environ.get("SUPERVISOR_TOKEN", "").strip()
    if not token:
        raise RuntimeError("SUPERVISOR_TOKEN not set. Are we running as an add-on?")
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

# -------------------------------
# SUPERVISOR API URL (correct for add-ons)
# -------------------------------
HA_URL = "http://supervisor/core/api"

# -------------------------------
# DIAGNOSTIC ENVIRONMENT LOGGING
# -------------------------------
print("=== MCP ENVIRONMENT CHECK ===", flush=True)
print(f"SUPERVISOR_TOKEN present: {bool(os.environ.get('SUPERVISOR_TOKEN'))}", flush=True)
print("=== END ENV CHECK ===", flush=True)

# -------------------------------
# HEALTH CHECK
# -------------------------------
@app.get("/")
def root():
    return {
        "status": "running",
        "supervisor_token_present": bool(os.environ.get("SUPERVISOR_TOKEN")),
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
            detail=f"Error contacting Supervisor API: {e}",
        )
    except RuntimeError as e:
        raise HTTPException(
            status_code=500,
            detail=str(e),
        )

    return {
        "home_assistant": {
            "version": config.get("version"),
            "location_name": config.get("location_name"),
            "time_zone": config.get("time_zone"),
            "unit_system": config.get("unit_system"),
            "installation_type": config.get("installation_type"),
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
# FUTURE MCP EXTENSIONS
# -------------------------------
# - entities
# - services
# - automations
# - dashboards
