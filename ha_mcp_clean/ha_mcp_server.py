# MCP Server v1.9.8
# Baseline: Overview, Entities, Devices, Areas, Services, Scripts, Automations, Events, Timers
# Dashboards endpoint: disabled with 501 error
# Version: 1.9.8

import os
import json
import logging
import requests
from fastapi import FastAPI, HTTPException

# -----------------------------------------------------------------------------
# Logging
# -----------------------------------------------------------------------------
logging.basicConfig(level=logging.INFO)
log = logging.getLogger("ha-mcp")

# -----------------------------------------------------------------------------
# FastAPI app
# -----------------------------------------------------------------------------
app = FastAPI(title="Home Assistant MCP Server")

# -----------------------------------------------------------------------------
# Global state
# -----------------------------------------------------------------------------
HA_TOKEN: str | None = None
HA_HTTP_BASE = "http://homeassistant:8123"

# -----------------------------------------------------------------------------
# Startup: capture token ONCE
# -----------------------------------------------------------------------------
@app.on_event("startup")
def startup():
    global HA_TOKEN
    log.info("=== MCP STARTUP BEGIN ===")
    log.info("Environment keys visible: %s", list(os.environ.keys()))
    HA_TOKEN = os.getenv("HA_TOKEN") or os.getenv("HASSIO_TOKEN") or os.getenv("SUPERVISOR_TOKEN")
    if not HA_TOKEN:
        raise RuntimeError("No Home Assistant token found in environment")
    log.info("✅ Home Assistant token captured and stored")
    log.info("=== MCP STARTUP COMPLETE ===")

# -----------------------------------------------------------------------------
# REST helper
# -----------------------------------------------------------------------------
def ha_rest_get(path: str):
    assert HA_TOKEN, "HA_TOKEN not initialised"
    resp = requests.get(
        f"{HA_HTTP_BASE}{path}",
        headers={"Authorization": f"Bearer {HA_TOKEN}"},
        timeout=15,
    )
    return resp

# -----------------------------------------------------------------------------
# Core API endpoints
# -----------------------------------------------------------------------------
@app.get("/api/overview")
def overview():
    resp = ha_rest_get("/api/config")
    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail="Failed to fetch overview data")
    config = resp.json()
    return {
        "home_assistant": {
            "version": config.get("version"),
            "location_name": config.get("name"),
            "time_zone": config.get("time_zone"),
            "unit_system": config.get("unit_system"),
            "installation_type": config.get("installation_type"),
        }
    }

@app.get("/api/entities")
def entities():
    resp = ha_rest_get("/api/states")
    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail="Failed to fetch entities")
    return {"count": len(resp.json()), "entities": resp.json()}

@app.get("/api/automations")
def automations():
    resp = ha_rest_get("/api/states")
    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail="Failed to fetch automations")
    return [s for s in resp.json() if s.get("entity_id", "").startswith("automation.")]

@app.get("/api/scripts")
def scripts():
    resp = ha_rest_get("/api/states")
    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail="Failed to fetch scripts")
    return [s for s in resp.json() if s.get("entity_id", "").startswith("script.")]

@app.get("/api/services")
def services():
    resp = ha_rest_get("/api/services")
    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail="Failed to fetch services")
    return resp.json()

@app.get("/api/devices")
def devices():
    resp = ha_rest_get("/api/config/device_registry")
    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail="Failed to fetch devices")
    return {"count": len(resp.json()), "devices": resp.json()}

@app.get("/api/areas")
def areas():
    resp = ha_rest_get("/api/config/area_registry")
    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail="Failed to fetch areas")
    return {"count": len(resp.json()), "areas": resp.json()}

@app.get("/api/events")
def events():
    resp = ha_rest_get("/api/events")
    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail="Failed to fetch events")
    events_list = resp.json()
    return {"count": len(events_list), "events": sorted(events_list)}

@app.get("/api/timers")
def timers():
    resp = ha_rest_get("/api/states")
    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail="Failed to fetch timers")
    timers_list = [s for s in resp.json() if s.get("entity_id", "").startswith("timer.")]
    return {"count": len(timers_list), "timers": timers_list}

# -----------------------------------------------------------------------------
# Dashboards endpoint disabled (v1.9.8)
# -----------------------------------------------------------------------------
@app.get("/api/dashboards")
def dashboards():
    raise HTTPException(
        status_code=501,
        detail="Dashboard fetch not available in current MCP configuration"
    )
