import os
import json
import asyncio
import logging
import requests
import websockets

from fastapi import FastAPI, HTTPException

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("ha-mcp")

app = FastAPI()

# -----------------------------------------------------------------------------
# Token separation (THIS IS THE IMPORTANT FIX)
# -----------------------------------------------------------------------------

HA_WS_TOKEN: str | None = None     # MUST be a Home Assistant long-lived token
HA_REST_TOKEN: str | None = None   # Supervisor token is fine for REST

HA_HTTP_BASE = "http://homeassistant:8123"
HA_WS_URL = "ws://homeassistant:8123/api/websocket"


# -----------------------------------------------------------------------------
# Startup: load tokens once and verify REST connectivity
# -----------------------------------------------------------------------------

@app.on_event("startup")
def startup():
    global HA_WS_TOKEN, HA_REST_TOKEN

    log.info("=== MCP STARTUP BEGIN ===")
    log.info("Environment keys visible: %s", list(os.environ.keys()))

    # WebSocket MUST use a real HA token
    HA_WS_TOKEN = os.getenv("HA_TOKEN")
    if not HA_WS_TOKEN:
        raise RuntimeError(
            "HA_TOKEN is required for WebSocket access (areas/devices)"
        )

    # REST can use supervisor token
    HA_REST_TOKEN = (
        os.getenv("SUPERVISOR_TOKEN")
        or os.getenv("HASSIO_TOKEN")
        or HA_WS_TOKEN
    )

    log.info("✅ Tokens loaded (WS + REST)")

    # Verify REST connectivity
    resp = requests.get(
        f"{HA_HTTP_BASE}/api/",
        headers={"Authorization": f"Bearer {HA_REST_TOKEN}"},
        timeout=10,
    )

    log.info("HA connectivity check status: %s", resp.status_code)

    if resp.status_code != 200:
        raise RuntimeError("Home Assistant REST validation failed")

    log.info("✅ Home Assistant connectivity confirmed")
    log.info("=== MCP STARTUP COMPLETE ===")


# -----------------------------------------------------------------------------
# Helper: WebSocket call wrapper (KNOWN WORKING)
# -----------------------------------------------------------------------------

async def ha_ws_call(command: dict) -> dict:
    assert HA_WS_TOKEN, "HA_WS_TOKEN not initialised"

    async with websockets.connect(HA_WS_URL) as ws:
        # Expect auth_required
        msg = json.loads(await ws.recv())
        if msg.get("type") != "auth_required":
            raise RuntimeError(f"Unexpected WS message: {msg}")

        # Authenticate
        await ws.send(json.dumps({
            "type": "auth",
            "access_token": HA_WS_TOKEN
        }))

        auth_reply = json.loads(await ws.recv())
        if auth_reply.get("type") != "auth_ok":
            raise RuntimeError(f"WebSocket auth failed: {auth_reply}")

        # Send command
        await ws.send(json.dumps(command))

        # Wait for result
        while True:
            reply = json.loads(await ws.recv())
            if reply.get("type") == "result":
                return reply


# -----------------------------------------------------------------------------
# Device + Area fetchers (WebSocket)
# -----------------------------------------------------------------------------

async def fetch_devices_ws():
    result = await ha_ws_call({
        "id": 1,
        "type": "config/device_registry/list",
    })
    return result.get("result", [])


async def fetch_areas_ws():
    result = await ha_ws_call({
        "id": 2,
        "type": "config/area_registry/list",
    })
    return result.get("result", [])


# -----------------------------------------------------------------------------
# API endpoints
# -----------------------------------------------------------------------------

@app.get("/api/devices")
async def devices():
    try:
        devices = await fetch_devices_ws()
        return {"count": len(devices), "devices": devices}
    except Exception as e:
        log.error("Devices WS fetch failed: %s", e)
        raise HTTPException(status_code=502, detail=str(e))


@app.get("/api/areas")
async def areas():
    try:
        areas = await fetch_areas_ws()
        return {"count": len(areas), "areas": areas}
    except Exception as e:
        log.error("Areas WS fetch failed: %s", e)
        raise HTTPException(status_code=502, detail=str(e))


@app.get("/api/entities")
def entities():
    resp = requests.get(
        f"{HA_HTTP_BASE}/api/states",
        headers={"Authorization": f"Bearer {HA_REST_TOKEN}"},
        timeout=10,
    )
    resp.raise_for_status()
    return {
        "count": len(resp.json()),
        "entities": resp.json(),
    }


# NOTE: Automations intentionally left as-is (known broken endpoint)
@app.get("/api/automations")
def automations():
    resp = requests.get(
        f"{HA_HTTP_BASE}/api/config/automation/config",
        headers={"Authorization": f"Bearer {HA_REST_TOKEN}"},
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()


@app.get("/api/tasks")
def tasks():
    return []


@app.get("/api/overview")
def overview():
    return {
        "status": "ok",
        "ws_token_loaded": HA_WS_TOKEN is not None,
        "rest_token_loaded": HA_REST_TOKEN is not None,
    }
