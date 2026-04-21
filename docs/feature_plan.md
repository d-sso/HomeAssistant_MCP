# Feature Plan

## Phase 1 — Read-only Tools (current)

### Discovery
- `list_entities` — filter by area, floor, domain, label, search string; paginated
- `list_devices` — physical devices with their linked entities
- `list_areas` / `list_floors` — spatial hierarchy
- `list_labels` — user-defined tags
- `list_domains` — active integrations/platforms

### State
- `get_state(entity_id)` — current state value + full attributes
- `get_states` — bulk query, filtered by area / domain / label / floor; paginated
- `get_unavailable_entities` — quick availability health check

### History (near-term)
- `get_history(entity_id, start, end)` — state change log over a time range
- `get_logbook(start, end, entity_id?)` — human-readable event narrative

### Configuration & Context
- `get_ha_config` — location, timezone, unit system, HA version
- `get_zones` — geographic zones (home, work, custom)
- `render_template(template)` — Jinja2 evaluation via HA template engine
- `get_calendars` — list calendar entities
- `get_calendar_events(entity_id, start, end)` — upcoming/past calendar events

### Scope Filtering (all tools)
- All tools automatically respect `HA_SCOPE_AREAS`, `HA_SCOPE_FLOORS`, `HA_SCOPE_DOMAINS`, `HA_SCOPE_LABELS` env vars
- Explicit filter params on each tool can override the server-level scope

---

## Phase 2 — Control Tools (TODO)

### Services
- `call_service(domain, service, data)` — generic service invocation
- `turn_on(entity_id)` / `turn_off(entity_id)` / `toggle(entity_id)` — convenience wrappers
- `set_value(entity_id, value)` — input helpers (boolean, number, text, select)
- `activate_scene(scene_id)`
- `run_script(script_id)`
- `trigger_automation(automation_id)`
- `send_notification(target, message, title?)` — via HA notify services

### Human Confirmation Gate (required before Phase 2 launch)
Control actions must be confirmed by a human before execution. Requires HA-side setup — see [architecture.md](architecture.md) for the proposed confirmation flow.

---

## Phase 3 — WebSocket / Event-driven (TODO)

- Subscribe to HA state change events
- Trigger an agent run in response to HA events (e.g. motion detected, door opened)
- Enables reactive/autonomous agent patterns
- Requires persistent connection management; more complex than REST polling

---

## Phase 4 — Long-term Statistics (TODO)

- `get_statistics(entity_id, period, start, end)` — min/max/mean/sum aggregates
- Uses HA's separate long-term stats storage (different API endpoint from history)
- Primary use case: energy-efficiency analysis, consumption trends, anomaly detection
- Enables agents specialised in performance reporting over weeks/months
