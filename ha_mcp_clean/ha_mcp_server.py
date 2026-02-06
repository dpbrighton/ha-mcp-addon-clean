from fastapi import FastAPI, HTTPException
import json
import os
import requests

app = FastAPI(title="Home Assistant MCP Server")

OPTIONS_PATH = "/data/options.json"
HA_URL = "http://homeassistant:8123/api"


def get_ha_token():
    if not os.path.exists(OPTIONS_PATH):
        raise RuntimeError("options.json not found (add-on config not saved)")

    with open(OPTIONS_PATH, "r") as f:
        options = json.load(f)

    token = options.get("ha_token", "").strip()
    if not token:
        raise RuntimeError("ha_token is empty in add-on configuration")

    return token


def get_ha_headers():
    token = get_ha_token()
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }


print("=== MCP OPTIONS CHECK ===", flush=True)
try:
    print("ha_token present:", bool(get_ha_token()), flush=True)
except Exception as e:
    print(f"❌ {e}", flush=True)
print("=== END OPTIONS CHECK ===", flush=True)


@app.get("/")
def root():
    try:
        get_ha_token()
        token_ok = True
    except Exception:
        token_ok = False

    return {
        "status": "running",
        "ha_token_present": token_ok
    }


@app.get("/api/overview")
def overview():
    try:
        headers = get_ha_headers()
        resp = requests.get(f"{HA_URL}/config", headers=headers, timeout=5)
        resp.raise_for_status()
        config = resp.json()
    except requests.RequestException as e:
        raise HTTPException(
            status_code=502,
            detail=f"Error contacting Home Assistant API: {e}"
        )
    except RuntimeError as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

    return {
        "home_assistant": {
            "version": config.get("version"),
            "location_name": config.get("name"),
            "time_zone": config.get("time_zone"),
            "unit_system": config.get("unit_system"),
            "installation_type": "homeassistant_os",
        }
    }
