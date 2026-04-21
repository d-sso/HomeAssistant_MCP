# Project Structure

## Repository scope

This repo (`homeassistant-mcp`) contains two runnable services that talk to Home Assistant:
- **MCP server** — exposes HA data as tools for AI agents
- **Bridge service** — syncs select entity states between environments via MQTT

HA configuration (YAML, automations, secrets) lives in a separate `homeassistant-config` repo.

---

## File scaffold

```
homeassistant-mcp/
│
├── server.py                      # MCP server entry point; registers all tools
│
├── ha_client.py                   # Shared HA REST client (used by MCP + bridge)
│                                  #   - auth header injection (Bearer token)
│                                  #   - base request/error handling
│                                  #   - scope filtering logic (HA_SCOPE_* env vars)
│                                  #   - pagination helpers
│
├── config.py                      # Reads environment variables; shared Config dataclass
│                                  #   HA_URL, HA_TOKEN
│                                  #   HA_SCOPE_AREAS, HA_SCOPE_FLOORS,
│                                  #   HA_SCOPE_DOMAINS, HA_SCOPE_LABELS
│                                  #   MQTT_HOST, MQTT_PORT, MQTT_TOPIC_PREFIX
│                                  #   BRIDGE_ENTITY_ALLOWLIST
│
├── tools/
│   ├── __init__.py
│   ├── discovery.py               # list_entities, list_devices, list_areas,
│   │                              # list_floors, list_labels, list_domains
│   ├── states.py                  # get_state, get_states, get_unavailable_entities
│   ├── history.py                 # get_history, get_logbook
│   ├── config_tools.py            # get_ha_config, get_zones, render_template,
│   │                              # get_calendars, get_calendar_events
│   └── (services.py)              # Phase 2: control tools (not yet implemented)
│
├── bridge/
│   ├── __init__.py
│   ├── prod_publisher.py          # Runs on/near prod: watches HA WebSocket,
│   │                              # publishes state changes to MQTT broker
│   ├── qa_subscriber.py           # Runs on/near QA: subscribes to MQTT broker,
│   │                              # pushes mirrored states into QA HA via REST
│   └── (command_gate.py)          # Phase 2: receives QA commands from MQTT,
│                                  # applies approval gate, forwards to prod HA
│
├── docs/
│   ├── README.md                  # Setup, installation, scope configuration guide
│   ├── feature_plan.md            # Phased feature roadmap
│   ├── design.md                  # Design decisions and rationale
│   ├── architecture.md            # Component diagrams, environment topology
│   ├── environments.md            # Dev / QA / Prod setup and promotion workflow
│   └── project_structure.md       # This file
│
├── tests/
│   ├── __init__.py
│   ├── test_ha_client.py          # Client auth, scope filtering, pagination
│   ├── test_discovery.py
│   ├── test_states.py
│   ├── test_history.py
│   ├── test_config_tools.py
│   └── bridge/
│       ├── test_prod_publisher.py
│       └── test_qa_subscriber.py
│
├── .env.example                   # Template for all env vars (MCP + bridge)
├── .env                           # Local secrets — gitignored
├── .gitignore
└── requirements.txt               # mcp, httpx, python-dotenv, paho-mqtt, websockets
```

---

## Module responsibilities

### `server.py`
- Instantiates the MCP server
- Imports and registers all tool functions from `tools/`
- Entry point: `python server.py`

### `ha_client.py`
- Single `HAClient` class shared by `tools/` and `bridge/`
- Exposes `get(path, params)` and `post(path, body)` methods
- `scope_filter(entities)` applies `HA_SCOPE_*` rules to any entity list

### `config.py`
- Reads `.env` via `python-dotenv`
- Single `Config` dataclass with typed fields for both MCP and bridge config
- Validates required vars on startup (fail fast with a clear error message)

### `tools/`
- Plain async functions; no MCP-specific imports — independently testable
- Receive a shared `HAClient` instance injected at server startup
- `server.py` wraps them with `@server.tool()` decorators

### `bridge/prod_publisher.py`
- Connects to prod HA WebSocket API
- Filters state change events against `BRIDGE_ENTITY_ALLOWLIST`
- Publishes `{MQTT_TOPIC_PREFIX}/states/<entity_id>` to MQTT broker
- Entry point: `python -m bridge.prod_publisher`

### `bridge/qa_subscriber.py`
- Subscribes to `{MQTT_TOPIC_PREFIX}/states/#` on MQTT broker
- Calls QA HA REST API to write mirrored entity states
- Entry point: `python -m bridge.qa_subscriber`

### `bridge/command_gate.py` *(Phase 2)*
- Subscribes to `{MQTT_TOPIC_PREFIX}/commands/#` from QA HA
- Checks command against allowlist; requests human approval if needed
- On approval, calls prod HA REST API to execute the service
- Entry point: `python -m bridge.command_gate`

---

## Key dependencies

| Package | Used by |
|---|---|
| `mcp` | MCP server — tool registration and stdio transport |
| `httpx` | `ha_client.py` — async HTTP to HA REST API |
| `websockets` | `bridge/prod_publisher.py` — HA WebSocket API |
| `paho-mqtt` | `bridge/` — MQTT publish/subscribe |
| `python-dotenv` | `config.py` — `.env` loading |

## Notes

- `tools/services.py` and `bridge/command_gate.py` are placeholders — not implemented until Phase 2
- Tests use `httpx` mock transport and a mock MQTT client; no live HA instance required
- `.env` is gitignored; `.env.example` documents every required variable
- HA config (YAML, automations, secrets) is managed in the separate `homeassistant-config` repo
