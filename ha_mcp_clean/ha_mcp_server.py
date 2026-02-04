from fastapi import FastAPI
import requests

app = FastAPI()

HA_URL = "http://supervisor/core/api"  # Home Assistant Supervisor API
HA_TOKEN = "<YOUR_LONG_LIVED_TOKEN>"  # Keep this in MCP config or options

HEADERS = {
    "Authorization": f"Bearer {HA_TOKEN}",
    "Content-Type": "application/json",
}

@app.get("/api/overview")
def overview():
    # existing overview code
    ...

@app.get("/api/entities")
def entities():
    """Return all entities, their domain, area, and state info"""
    url = "http://supervisor/core/api/states"
    resp = requests.get(url, headers=HEADERS)
    resp.raise_for_status()
    states = resp.json()
    
    # Structure the data for AI client
    data = []
    for entity in states:
        data.append({
            "entity_id": entity.get("entity_id"),
            "state": entity.get("state"),
            "attributes": entity.get("attributes"),
            "area": entity.get("attributes", {}).get("area_id"),
            "domain": entity.get("entity_id").split(".")[0]
        })
    return {"entities": data}
