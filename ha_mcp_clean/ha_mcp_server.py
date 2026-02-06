# ha_mcp_server.py
import os
from fastapi import FastAPI, HTTPException

app = FastAPI(title="Home Assistant MCP Server")

# Global storage for HA_TOKEN
HA_TOKEN = None

@app.on_event("startup")
def startup_event():
    global HA_TOKEN
    # Read HA_TOKEN from environment once at startup
    HA_TOKEN = os.environ.get("HA_TOKEN")
    print("ENVIRONMENT VARIABLES AT STARTUP:", os.environ)  # Debug: confirm token is visible
    if not HA_TOKEN:
        raise RuntimeError("❌ HA_TOKEN not set or empty. Check add-on config.")

@app.get("/api/overview")
def get_overview():
    if not HA_TOKEN:
        raise HTTPException(status_code=500, detail="HA_TOKEN not set at runtime")
    # TODO: Replace with real MCP overview retrieval logic
    return {"message": "Overview retrieved successfully", "ha_token_length": len(HA_TOKEN)}

@app.get("/api/entities")
def get_entities():
    if not HA_TOKEN:
        raise HTTPException(status_code=500, detail="HA_TOKEN not set at runtime")
    # TODO: Replace with real MCP entities retrieval logic
    return {"message": "Entities retrieved successfully", "ha_token_length": len(HA_TOKEN)}
