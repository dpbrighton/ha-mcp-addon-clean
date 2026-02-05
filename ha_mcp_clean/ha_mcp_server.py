from fastapi import FastAPI
import os
import requests

app = FastAPI(title="Home Assistant MCP Server")

# Home Assistant Supervisor API base URL
HA_URL = "http://supervisor/core/api"

# Read token injected by Home Assistant add-on options
HA_TOKEN = os.environ.get("HA_TOKEN")

if not HA_TOKEN:
    # Fail loudly so it appears in add-on logs
    raise RuntimeError(
        "HA_TOKEN not set. Add-on options must define ha_token."
    )

HEADERS = {
    "Authorization": f"Bearer {HA_TOKEN}",
    "Content-Type": "application/json",
}


@app.get("/")
def root():
    """Sanity check endpoint"""
    return {"status": "ok", "service": "ha-mcp"}


@app.get("/api/overview")
def overview():
    """
    Diagnostic overview endpoint.
    Returns raw Home Assistant response so we can see exactly what HA returns.
    """
    try:
        resp = requests.get(
            f"{HA_URL}/config",
            headers=HEADERS,
            timeout=5,
        )

        return {
            "debug": True,
            "ha_url": f"{HA_URL}/config",
            "status_code": resp.status_code,
            "response_text": resp.text,
        }

    except Exception as e:
        return {
            "debug": True,
            "exception": str(e),
            "ha_url": HA_URL,
        }
