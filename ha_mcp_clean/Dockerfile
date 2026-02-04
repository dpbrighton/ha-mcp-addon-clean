ARG BUILD_FROM
FROM ${BUILD_FROM}

RUN apk add --no-cache \
    python3 \
    py3-pip \
    py3-requests

RUN pip3 install --no-cache-dir --break-system-packages \
    fastapi \
    uvicorn

COPY ha_mcp_server.py /app/ha_mcp_server.py
WORKDIR /app

# This line passes the HA token from Home Assistant options into the container
ENV HA_TOKEN=${ha_token}

CMD ["uvicorn", "ha_mcp_server:app", "--host", "0.0.0.0", "--port", "8000"]
