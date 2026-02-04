from fastapi import FastAPI

app = FastAPI()

# Existing root endpoint
@app.get("/")
def root():
    return {
        "status": "ok",
        "message": "Home Assistant MCP running"
    }

# --- NEW: Overview endpoint ---
@app.get("/api/overview")
def overview():
    return {
        "home_assistant": {
            "version": "2024.12.1",
            "installation_type": "Home Assistant OS",
            "location_name": "Home",
            "time_zone": "Europe/London",
            "currency": "GBP",
            "unit_system": {
                "length": "metric",
                "mass": "metric",
                "temperature": "celsius"
            }
        },
        "counts": {
            "areas": 7,
            "devices": 68,
            "entities": 214,
            "automations": 43,
            "scripts": 19,
            "dashboards": 3
        }
    }
