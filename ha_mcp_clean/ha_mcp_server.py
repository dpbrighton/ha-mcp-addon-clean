from fastapi import FastAPI, HTTPException
import requests

app = FastAPI(title="Home Assistant MCP Server")

# ===== TEMPORARY HARD-CODED TOKEN FOR TESTING =====
HA_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiIwOWU0NGRkM2Q3YWI0OWExYmQ4YTE1OGRiZWY5MWJmMyIsImlhdCI6MTc2ODgyMDk5NiwiZXhwIjoyMDg0MTgwOTk2fQ.rp9vAIImtNuLmANGWQAbwxgPH4MpUoHeRNH0qPFPHCI"  # Replace with your actual token
print(f"Using HA_TOKEN: {HA_TOKEN[:8]}... (truncated)")

HEADERS = {
    "Authorization": f"Bearer {HA_TOKEN}",
    "Content-Type": "application/json",
}

HA_URL = "http://supervisor/core/api"  # Supervisor API endpoint

@app.get("/api/overview")
def overview():
    """Return a summary of Home Assistant environment and counts."""
    try:
        resp = requests.get(f"{HA_URL}/config", headers=HEADERS, timeout=5)
        resp.raise_for_status()
        config = resp.json()
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=f"Error contacting HA API: {e}")

    # Dummy counts for demonstration; can expand to real counts later
    return {
        "home_assistant": {
            "version": config.get("version"),
            "installation_type": config.get("installation_type"),
            "location_name": config.get("location_name"),
            "time_zone": config.get("time_zone"),
            "unit_system": config.get("unit_system"),
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

# Optional: keep /api/tasks placeholder for Mac client to stop showing 404s
@app.get("/api/tasks")
def tasks():
    return {"tasks": []}
