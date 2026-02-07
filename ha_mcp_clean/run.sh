#!/usr/bin/with-contenv bashio

bashio::log.info "MCP startup wrapper running"

HA_TOKEN="$(bashio::config 'ha_token')"

if [[ -z "$HA_TOKEN" ]]; then
  bashio::log.error "ha_token is missing or empty"
  exit 1
fi

export HA_TOKEN

bashio::log.info "ha_token loaded successfully"

exec uvicorn ha_mcp_server:app --host 0.0.0.0 --port 8000
