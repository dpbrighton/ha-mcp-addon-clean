# -----------------------------------------------------------------------------
# MCP Server v2.0.0
# Improvements:
#   - Enriched entity responses (friendly_name, curated attributes)
#   - Domain filtering on /api/entities?domain=light
#   - Dedicated /api/battery endpoint with red/amber/green status
#   - Single entity detail: GET /api/entity/{entity_id}
#   - Write support: POST /api/call_service (turn lights on/off, etc.)
#   - Real counts in /api/overview
#   - POST /api/automation/trigger and /api/script/run
# -----------------------------------------------------------------------------

import os
import json
import logging
import requests
import websockets
import asyncio
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from typing import Optional

# -----------------------------------------------------------------------------
# Logging
# -----------------------------------------------------------------------------
logging.basicConfig(level=logging.INFO)
log = logging.getLogger("ha-mcp")

# -----------------------------------------------------------------------------
# FastAPI app
# -----------------------------------------------------------------------------
app = FastAPI(title="Home Assistant MCP Server", version="2.0.0")

# -----------------------------------------------------------------------------
# Global state
# -----------------------------------------------------------------------------
HA_TOKEN: str | None = None
HA_HTTP_BASE = "http://homeassistant:8123"
HA_WS_URL = "ws://homeassistant:8123/api/websocket"

# -----------------------------------------------------------------------------
# Startup
# -----------------------------------------------------------------------------
@app.on_event("startup")
def startup():
    global HA_TOKEN
    log.info("=== MCP STARTUP BEGIN ===")
    HA_TOKEN = (
        os.getenv("HA_TOKEN")
        or os.getenv("HASSIO_TOKEN")
        or os.getenv("SUPERVISOR_TOKEN")
    )
    if not HA_TOKEN:
        raise RuntimeError("No Home Assistant token found in environment")
    log.info("✅ HA token captured (len=%d)", len(HA_TOKEN))
    log.info("=== MCP STARTUP COMPLETE ===")

# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------
def _headers():
    return {"Authorization": f"Bearer {HA_TOKEN}", "Content-Type": "application/json"}

def ha_get(path: str):
    assert HA_TOKEN
    return requests.get(f"{HA_HTTP_BASE}{path}", headers=_headers(), timeout=15)

def ha_post(path: str, payload: dict):
    assert HA_TOKEN
    return requests.post(f"{HA_HTTP_BASE}{path}", headers=_headers(), json=payload, timeout=15)

def _enrich(entity: dict) -> dict:
    """Return a clean, LLM-friendly representation of an HA entity state."""
    attrs = entity.get("attributes", {})
    # Pull out the most useful attributes; drop noisy/UI-only ones
    skip = {"entity_picture", "icon", "entity_picture_local", "supported_features",
            "supported_color_modes", "color_mode", "effect_list", "hs_color",
            "xy_color", "min_mireds", "max_mireds"}
    curated = {k: v for k, v in attrs.items() if k not in skip}
    return {
        "entity_id": entity["entity_id"],
        "domain": entity["entity_id"].split(".")[0],
        "friendly_name": attrs.get("friendly_name", entity["entity_id"]),
        "state": entity["state"],
        "last_changed": entity.get("last_changed"),
        "attributes": curated,
    }

async def ha_ws_call(command: dict) -> dict:
    assert HA_TOKEN
    async with websockets.connect(HA_WS_URL) as ws:
        msg = json.loads(await ws.recv())
        if msg.get("type") != "auth_required":
            raise RuntimeError(f"Unexpected WS message: {msg}")
        await ws.send(json.dumps({"type": "auth", "access_token": HA_TOKEN}))
        auth_reply = json.loads(await ws.recv())
        if auth_reply.get("type") != "auth_ok":
            raise RuntimeError(f"WebSocket auth failed: {auth_reply}")
        await ws.send(json.dumps(command))
        while True:
            reply = json.loads(await ws.recv())
            if reply.get("type") == "result":
                return reply

# -----------------------------------------------------------------------------
# Overview — real counts
# -----------------------------------------------------------------------------
@app.get("/api/overview")
def overview():
    config_resp = ha_get("/api/config")
    states_resp = ha_get("/api/states")
    if config_resp.status_code != 200:
        raise HTTPException(status_code=502, detail="Failed to fetch HA config")
    config = config_resp.json()
    states = states_resp.json() if states_resp.status_code == 200 else []
    domains: dict[str, int] = {}
    for s in states:
        d = s.get("entity_id", "").split(".")[0]
        domains[d] = domains.get(d, 0) + 1
    return {
        "home_assistant": {
            "version": config.get("version"),
            "location_name": config.get("name"),
            "time_zone": config.get("time_zone"),
            "unit_system": config.get("unit_system"),
            "installation_type": config.get("installation_type"),
        },
        "entity_counts_by_domain": domains,
        "total_entities": len(states),
    }

# -----------------------------------------------------------------------------
# Entities — with domain filter and enrichment
# -----------------------------------------------------------------------------
@app.get("/api/entities")
def entities(domain: Optional[str] = Query(None, description="Filter by domain, e.g. light, switch, sensor")):
    resp = ha_get("/api/states")
    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail="Failed to fetch entities")
    all_states = resp.json()
    if domain:
        all_states = [s for s in all_states if s.get("entity_id", "").startswith(f"{domain}.")]
    enriched = [_enrich(s) for s in all_states]
    return {"count": len(enriched), "domain_filter": domain, "entities": enriched}

# -----------------------------------------------------------------------------
# Single entity detail
# -----------------------------------------------------------------------------
@app.get("/api/entity/{entity_id:path}")
def entity_detail(entity_id: str):
    resp = ha_get(f"/api/states/{entity_id}")
    if resp.status_code == 404:
        raise HTTPException(status_code=404, detail=f"Entity '{entity_id}' not found")
    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail="Failed to fetch entity")
    return _enrich(resp.json())

# -----------------------------------------------------------------------------
# Battery status — red/amber/green
# -----------------------------------------------------------------------------
@app.get("/api/battery")
def battery():
    resp = ha_get("/api/states")
    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail="Failed to fetch entities")
    result = []
    for entity in resp.json():
        attrs = entity.get("attributes", {})
        level = attrs.get("battery_level") or attrs.get("battery")
        if level is None:
            # Also check entities whose domain is 'sensor' and unit is '%' with 'battery' in ID
            if (entity.get("entity_id", "").find("battery") != -1
                    and attrs.get("unit_of_measurement") == "%"):
                try:
                    level = float(entity["state"])
                except (ValueError, TypeError):
                    continue
        if level is None:
            continue
        try:
            level = int(float(level))
        except (ValueError, TypeError):
            continue
        if level >= 60:
            status = "green"
        elif level >= 20:
            status = "amber"
        else:
            status = "red"
        result.append({
            "entity_id": entity["entity_id"],
            "friendly_name": attrs.get("friendly_name", entity["entity_id"]),
            "battery_level": level,
            "status": status,
        })
    result.sort(key=lambda x: x["battery_level"])
    return {"count": len(result), "devices": result}

# -----------------------------------------------------------------------------
# Call a service (write/control)
# -----------------------------------------------------------------------------
class ServiceCall(BaseModel):
    domain: str
    service: str
    entity_id: Optional[str] = None
    service_data: Optional[dict] = None

@app.post("/api/call_service")
def call_service(call: ServiceCall):
    """
    Call any Home Assistant service.
    Examples:
      {"domain":"light","service":"turn_on","entity_id":"light.living_room","service_data":{"brightness_pct":80}}
      {"domain":"switch","service":"turn_off","entity_id":"switch.kettle"}
      {"domain":"climate","service":"set_temperature","entity_id":"climate.living_room","service_data":{"temperature":21}}
    """
    payload = call.service_data or {}
    if call.entity_id:
        payload["entity_id"] = call.entity_id
    resp = ha_post(f"/api/services/{call.domain}/{call.service}", payload)
    if resp.status_code not in (200, 201):
        raise HTTPException(status_code=502, detail=f"Service call failed ({resp.status_code}): {resp.text}")
    return {"success": True, "result": resp.json() if resp.content else []}

# -----------------------------------------------------------------------------
# Automations
# -----------------------------------------------------------------------------
@app.get("/api/automations")
def automations():
    resp = ha_get("/api/states")
    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail="Failed to fetch automations")
    items = [_enrich(s) for s in resp.json() if s.get("entity_id", "").startswith("automation.")]
    return {"count": len(items), "automations": items}

@app.post("/api/automation/trigger")
def trigger_automation(entity_id: str):
    resp = ha_post(f"/api/services/automation/trigger", {"entity_id": entity_id})
    if resp.status_code not in (200, 201):
        raise HTTPException(status_code=502, detail=f"Trigger failed: {resp.text}")
    return {"success": True}

# -----------------------------------------------------------------------------
# Scripts
# -----------------------------------------------------------------------------
@app.get("/api/scripts")
def scripts():
    resp = ha_get("/api/states")
    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail="Failed to fetch scripts")
    items = [_enrich(s) for s in resp.json() if s.get("entity_id", "").startswith("script.")]
    return {"count": len(items), "scripts": items}

@app.post("/api/script/run")
def run_script(entity_id: str):
    script_name = entity_id.replace("script.", "")
    resp = ha_post(f"/api/services/script/{script_name}", {})
    if resp.status_code not in (200, 201):
        raise HTTPException(status_code=502, detail=f"Script run failed: {resp.text}")
    return {"success": True}

# -----------------------------------------------------------------------------
# Services catalogue
# -----------------------------------------------------------------------------
@app.get("/api/services")
def services(domain: Optional[str] = Query(None, description="Filter by domain, e.g. light")):
    resp = ha_get("/api/services")
    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail="Failed to fetch services")
    data = resp.json()
    if domain:
        data = [s for s in data if s.get("domain") == domain]
    return data

# -----------------------------------------------------------------------------
# Devices & Areas (WebSocket registry)
# -----------------------------------------------------------------------------
@app.get("/api/devices")
async def devices():
    devs = await ha_ws_call({"id": 1, "type": "config/device_registry/list"})
    items = devs.get("result", [])
    return {"count": len(items), "devices": items}

@app.get("/api/areas")
async def areas():
    result = await ha_ws_call({"id": 2, "type": "config/area_registry/list"})
    items = result.get("result", [])
    return {"count": len(items), "areas": items}

# -----------------------------------------------------------------------------
# Events
# -----------------------------------------------------------------------------
@app.get("/api/events")
async def events():
    result = await ha_ws_call({"id": 3, "type": "get_event_types"})
    items = result.get("result", [])
    return {"count": len(items), "events": sorted(items)}

# -----------------------------------------------------------------------------
# Timers
# -----------------------------------------------------------------------------
@app.get("/api/timers")
def timers():
    resp = ha_get("/api/states")
    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail="Failed to fetch timers")
    items = [_enrich(s) for s in resp.json() if s.get("entity_id", "").startswith("timer.")]
    return {"count": len(items), "timers": items}
