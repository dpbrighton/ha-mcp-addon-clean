# -------------------------------------------------------------------
# Automations endpoint (diagnostic)
# -------------------------------------------------------------------
@app.get("/api/automations")
def automations():
    url = f"{HA_API_BASE}/config/automation/config"
    log(f"[DIAG] Fetching Automations from: {url}")
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        log(f"[DIAG] Automations status: {resp.status_code}")
        log(f"[DIAG] Automations response: {resp.text[:500]}")  # first 500 chars
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as e:
        log(f"[DIAG] Automations fetch failed: {e}")
        data = {"error": str(e)}
    return data

# -------------------------------------------------------------------
# Devices endpoint (diagnostic)
# -------------------------------------------------------------------
@app.get("/api/devices")
def devices():
    url = f"{HA_API_BASE}/config/device_registry/list"
    log(f"[DIAG] Fetching Devices from: {url}")
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        log(f"[DIAG] Devices status: {resp.status_code}")
        log(f"[DIAG] Devices response: {resp.text[:500]}")
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as e:
        log(f"[DIAG] Devices fetch failed: {e}")
        data = {"error": str(e)}
    return data

# -------------------------------------------------------------------
# Areas endpoint (diagnostic)
# -------------------------------------------------------------------
@app.get("/api/areas")
def areas():
    url = f"{HA_API_BASE}/config/area_registry/list"
    log(f"[DIAG] Fetching Areas from: {url}")
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        log(f"[DIAG] Areas status: {resp.status_code}")
        log(f"[DIAG] Areas response: {resp.text[:500]}")
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as e:
        log(f"[DIAG] Areas fetch failed: {e}")
        data = {"error": str(e)}
    return data
