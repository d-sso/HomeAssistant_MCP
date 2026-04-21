# Architecture

## Repository boundaries

```
homeassistant-config/   (separate repo)
  HA YAML, automations,
  secrets template,
  Docker Compose for
  dev + QA HA instances
           │
           │ deploys
           ▼
    Home Assistant
    (dev / QA / prod)
           ▲
           │ REST API / WebSocket
           │
homeassistant-mcp/   (this repo)
  MCP server + bridge service
```

---

## Phase 1 — Read-only MCP Server

```
┌─────────────────────────────────────────────────────────┐
│  Agent layer                                            │
│                                                         │
│  Claude Code          Custom agent (Anthropic SDK)      │
│  (MCP client)         (MCP client)                      │
└────────────┬──────────────────────┬─────────────────────┘
             │ stdio (MCP protocol) │ stdio (MCP protocol)
             ▼                      ▼
┌─────────────────────────────────────────────────────────┐
│  MCP Server  (server.py)                                │
│                                                         │
│  ┌─────────────┐  ┌──────────────┐  ┌───────────────┐  │
│  │  Discovery  │  │    State     │  │    History    │  │
│  │   tools     │  │    tools     │  │    tools      │  │
│  └──────┬──────┘  └──────┬───────┘  └───────┬───────┘  │
│         └────────────────┼──────────────────┘           │
│                          │                              │
│              ┌───────────▼──────────┐                   │
│              │   ha_client.py       │                   │
│              │  (auth, base HTTP,   │                   │
│              │   scope filtering)   │                   │
│              └───────────┬──────────┘                   │
│                          │                              │
│              ┌───────────▼──────────┐                   │
│              │   config.py          │                   │
│              │  (HA_URL, HA_TOKEN,  │                   │
│              │   HA_SCOPE_* vars)   │                   │
│              └──────────────────────┘                   │
└──────────────────────────┬──────────────────────────────┘
                           │ HTTPS REST
                           ▼
              ┌────────────────────────┐
              │   Home Assistant       │
              │   REST API  /api/*     │
              └────────────────────────┘
```

### Multiple scoped instances

The same `server.py` binary runs as separate processes with different `HA_SCOPE_*` env vars. Claude Code registers each as a distinct named MCP server — agents are wired to the instance that matches their scope.

```
ha-global   → server.py (no scope — all entities)
ha-bedroom  → server.py (HA_SCOPE_AREAS=bedroom)
ha-living   → server.py (HA_SCOPE_AREAS=living_room)
ha-energy   → server.py (HA_SCOPE_DOMAINS=sensor,energy)
```

---

## Environment topology (Dev / QA / Prod)

```
┌──────────────────────────────────────────────────────────────────┐
│  PROD (physical network)                                         │
│                                                                  │
│  Real devices ──── Home Assistant (prod) ──── prod_publisher.py  │
│  (Zigbee, WiFi,    ZHA, integrations             │               │
│   cloud svcs)      HA_URL=prod                   │               │
└──────────────────────────────────────────────────┼───────────────┘
                                                   │ MQTT publish
                                                   │ ha/states/<id>
                                        ┌──────────▼──────────┐
                                        │   MQTT Broker        │
                                        │   (host network)     │
                                        └──────────┬──────────┘
                                                   │ MQTT subscribe
┌──────────────────────────────────────────────────┼───────────────┐
│  QA (Docker network)                             │               │
│                                                  │               │
│  Home Assistant (QA) ◄──── qa_subscriber.py ─────┘               │
│  HA_URL=qa             mirrors select entities                    │
│  (no real devices)     via REST API                              │
│         ▲                                                        │
│         │ REST / stdio                                           │
│  MCP server (QA scope) ◄── agent under test                      │
└──────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│  DEV (Docker network, fully isolated)                            │
│                                                                  │
│  Home Assistant (dev) ── restored from backup, fake credentials  │
│  (no device connectivity; entities may be unavailable)           │
│         ▲                                                        │
│         │ REST / stdio                                           │
│  MCP server (dev scope) ◄── agent under development             │
└──────────────────────────────────────────────────────────────────┘
```

### MQTT bridge flow (QA state sync)

```
Prod HA                prod_publisher.py          MQTT broker
  │                           │                        │
  │  state_changed event      │                        │
  │ (WebSocket)               │                        │
  ├──────────────────────────►│                        │
  │                           │  publish               │
  │                           │  ha/states/<entity_id> │
  │                           ├───────────────────────►│
  │                                                    │
                                                       │  subscribe
                                                       │  ha/states/#
                                            qa_subscriber.py
                                                       │
                                                       │  POST /api/states/<id>
                                                       ▼
                                                   QA HA
```

Only entities on `BRIDGE_ENTITY_ALLOWLIST` are published. The allowlist is the mechanism for selective real-world testing in QA.

---

## Phase 2 — Control Tools with Human Confirmation (TODO)

Control actions require explicit human approval before execution.

```
Agent              MCP Server          Home Assistant         Human
  │                    │                     │                  │
  │  call_service(..)  │                     │                  │
  ├───────────────────►│                     │                  │
  │                    │  notify.persistent  │                  │
  │                    ├────────────────────►│                  │
  │                    │                     │  notification    │
  │                    │                     ├─────────────────►│
  │  { pending,        │                     │                  │
  │    token: "abc" }  │                     │  approve / deny  │
  │◄───────────────────┤                     │◄─────────────────┤
  │                    │  webhook (decision) │                  │
  │                    │◄────────────────────┤                  │
  │  { approved }      │                     │                  │
  │◄───────────────────┤                     │                  │
  │                    │  POST /api/services │                  │
  │                    ├────────────────────►│                  │
  │  { executed }      │                     │                  │
  │◄───────────────────┤                     │                  │
```

### HA-side requirements (to be designed in detail — homeassistant-config repo)
- Persistent notification service to surface approval requests
- Automation: listens for approve/deny on notification, fires webhook back to MCP server
- Short-lived token per pending action for correlation
- Configurable timeout — auto-deny if no human response within N seconds

### QA command gate (Phase 2 bridge extension)

```
QA HA  ──►  command_gate.py  ──MQTT──►  prod_command_listener.py  ──►  Prod HA
              (allowlist +                   (executes approved
               approval gate)                 service calls)
```

---

## Phase 3 — WebSocket / Event-driven (TODO)

```
Prod HA               prod_publisher.py         Agent runtime
WebSocket API         (persistent conn)
      │                      │                        │
      │  state_changed event │                        │
      ├─────────────────────►│                        │
      │                      │  match trigger rules   │
      │                      │  spawn / wake agent    │
      │                      ├───────────────────────►│
      │                      │                        │  runs with event ctx
```

Note: `prod_publisher.py` already uses WebSocket for bridge state sync. Phase 3 extends it with trigger rules and agent spawning — not a new process, an extension of the bridge.

---

## Phase 4 — Long-term Statistics (TODO)

Uses HA's `/api/statistics` endpoint (separate from `/api/history`). Data is pre-aggregated into hourly/daily buckets. Primary consumer: energy-efficiency agents querying weeks or months of consumption data.
