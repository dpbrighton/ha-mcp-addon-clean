import os
import yaml
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Home Assistant MCP Server")

# Allow all CORS (adjust if needed)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Read HA token from config.yaml at startup
CONFIG_PATH = "/data/options.yaml"  # Home Assistant add-ons use options.yaml
ha_token = None

def load_config():
    global ha_token
    try:
        with open(CONFIG_PATH, "r") as f:
            config = yaml.safe_load(f)
            ha_token = config.get("ha_token")
            if not ha_token:
                raise RuntimeError("❌ HA_TOKEN not set or empty in config.yaml")
            print(f"✅ HA_TOKEN successfully loaded at startup")
    except FileNotFoundError:
        raise RuntimeError(f"❌ Config file not found at {CONFIG_PATH}")
    except Exception as e:
        raise RuntimeError(f"❌ Error loading config: {e}")

# Load the token at startup
load_config()

# Store the token for reuse in requests
@app.on_event("startup")
def startup_event():
    if not ha_token:
        raise RuntimeError("❌ HA_TOKEN not set or empty. Check add-on config.")
    print("✅ Application startup complete. HA_TOKEN ready for use.")

# Example endpoint using the token
@app.get("/api/overview")
def get_overview():
    # This is where your previous logic fetching Home Assistant data goes
    # Example return:
    return {"status": "ok", "ha_token_present": bool(ha_token)}

@app.get("/api/entities")
def get_entities():
    # Example return:
    return {"status": "ok", "ha_token_present": bool(ha_token)}

# You can now safely use ha_token in any other function without re-reading config
