# OmniRoute & 9router Integration

If you use **OmniRoute** or **9router** as your network reverse-proxy, you can use `llm-gate` as the intelligent evaluation layer to dictate the routing targets.

### Critical Production Notes (Port Conflicts & Security)

Both 9router and OmniRoute are known to default to port `20128`. If you are running them concurrently on the same host, OminRoute will fail to start.

When orchestrating them alongside `llm-gate`, map your ports distinctly:
* `9router`: Port 20128
* `OmniRoute`: Port 20129
* `llm-gate` (serve mode): Port 8000

#### OmniRoute Docker Compose Example:
```yaml
services:
  omniroute:
    image: omniroute:latest
    ports:
      - "20129:20128" # Remapped to avoid 9router conflict
    environment:
      # Safety limits for existing DB migrations
      - OMNIROUTE_MAX_PENDING_MIGRATIONS=0
      - DATA_DIR=/app/data
      - GATE = http://llm-gate:8000/v1/route
```

**Note on Healthchecks:** OmniRoute's management UI redirects `/` to `/dashboard` and `/login`. Unauthenticated pings to `/api/health` will return a `401 Unauthorized` by design. Do not use `/api/health` for your Docker container healthcheck unless you pass an admin token.

When configured, OmniRoute handles the SSE stream, and `llm-gate` ensures the routing policy respects criticality.
