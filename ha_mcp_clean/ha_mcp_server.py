import os
import json
import requests
from fastapi import FastAPI
from fastapi.responses import JSONResponse

# -------------------------------------------------------------------
# Configuration
# -------------------------------------------------------------------

HA_HTTP_BASE = os.getenv("HA_HTTP_BASE", "http://homeassistant:8123")
HA_TOKEN = os.getenv("HA_TOKEN")
HA_WS_TOKEN = os.getenv("HA_WS_TOKEN")  # optional

if not HA_TOKEN:
    raise RuntimeError("HA_TOKEN not set")

HEADERS = {
    "Authorization": f"Bearer {HA_TOKEN}",
    "Content-Type": "application/json",
}

app = FastAPI(title="Home Assistant MCP Server")

# -------------------------------------------------------------------
# Helpers
# -------------------------------------------------------------------

def ha_get(path: str):
    resp = requests.get(
        f"{HA_HTTP_BASE}{path}",
        headers=HEADERS,
        timeout=10,
    )
    resp.raise_for_status()
    return resp


def safe_json_or_text(resp):
    """
    Home Assistant sometimes returns YAML or mixed content.
    This prevents JSONDecodeError crashes.
    """
    ctype = resp.headers.get("content-type", "")
    if "application/json" in ctype:
        return resp.json()
    return {
        "raw": resp.text,
        "content_type": ctype,
    }

# -------------------------------------------------------------------
# API Endpoints
# -------------------------------------------------------------------

@app.get("/api/overview")
def overview():
    resp = ha_get("/api/")
    return safe_json_or_text(resp)


@app.get("/api/entities")
def entities():
    resp = ha_get("/api/states")
    return resp.json()


@app.get("/api/devices")
def devices():
    resp = ha_get("/api/config/device_registry/list")
    return resp.json()


@app.get("/api/areas")
def areas():
    resp = ha_get("/api/config/area_registry/list")
    return resp.json()


@app.get("/api/tasks")
def tasks():
    # Placeholder – HA does not have a stable "tasks" endpoint
    return []


@app.get("/api/automations")
def automations():
    """
    THIS WAS THE CRASHING ENDPOINT.
    HA may return YAML or mixed content here.
    """
    resp = ha_get("/api/config/automation/config")
    return safe_json_or_text(resp)


# -------------------------------------------------------------------
# Startup diagnostics
# -------------------------------------------------------------------

@app.on_event("startup")
def startup_log():
    print("MCP startup wrapper running")
    print("HA_TOKEN loaded successfully")

    if not HA_WS_TOKEN:
        print("HA_WS_TOKEN not set – WebSocket calls will fail")
    else:
        print("HA_WS_TOKEN detected (WebSocket enabled)")
