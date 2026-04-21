# Environments

## Overview

Three environments exist for developing, validating, and running AI agents against Home Assistant. Each has a distinct isolation level and purpose.

| | Dev | QA | Prod |
|---|---|---|---|
| **HA instance** | Docker (isolated) | Docker (MQTT-bridged) | Physical host |
| **Real devices** | None — network isolated | Read-only mirror of select entities | All devices |
| **Agent writes** | Allowed (safe — no real devices) | Controlled via command gate (Phase 2) | Human confirmation required |
| **Data source** | Backup restore + frozen states | Live mirror via MQTT bridge | Live |
| **Purpose** | Tool development, MCP logic | Validate agent behaviour with real data | Production use |

---

## Dev environment

### What it is
A Docker-hosted HA instance restored from a production backup, running on an isolated bridge network with no access to the physical device network.

### What it's good for
- Developing and testing MCP tool logic
- Testing agent prompts and tool call sequences
- Validating scope filtering, pagination, and error handling
- Safe for agents to call control tools — no real devices can respond

### Key behaviours
- Integrations that require physical devices will show entities as `unavailable` — this is expected and acceptable
- Cloud integrations (e.g. weather, Spotify, Google) will fail unless re-credentialled with test accounts — disable or leave unavailable
- HA long-lived token is a dev-only credential, never shared with QA or prod

### Setup
1. Restore a production backup into the Docker instance (see `homeassistant-config` repo)
2. Run `setup_secrets.py --env dev` to replace credentials with safe test values
3. Start with `docker compose -f docker/dev/docker-compose.yml up`
4. Point MCP server at dev HA: `HA_URL=http://localhost:8123` (dev token)

### Backup hygiene
- Backups contain real credentials — never commit a raw backup to Git
- The restore + sanitization script (`homeassistant-config/scripts/setup_secrets.py`) handles credential replacement as part of the restore workflow
- Maintain a "blessed dev snapshot" — a sanitized backup that can be restored repeatedly for consistent test state

---

## QA environment

### What it is
A Docker-hosted HA instance that mirrors the state of selected prod entities in near-real-time via the MQTT bridge. It has no direct device connectivity but reflects real-world state.

### What it's good for
- Validating agent decision-making against live data
- Testing automation logic before deploying to prod
- Staged rollout: onboard an agent to QA first, observe, then promote to prod
- Integration testing of the full MCP → HA → bridge → MQTT stack

### Key behaviours
- Entity states are read from prod via MQTT — not from real devices directly
- Entities not on `BRIDGE_ENTITY_ALLOWLIST` show as `unavailable` (same as dev)
- Agent writes are blocked at the MCP layer in Phase 1 (read-only)
- Phase 2: writes go through `command_gate.py` — allowlisted commands may reach prod devices; all others are blocked

### MQTT bridge setup
1. Start the MQTT broker on the host (reachable from both prod network and Docker QA network)
2. Run `prod_publisher.py` on/near prod HA — configure `BRIDGE_ENTITY_ALLOWLIST`
3. Run `qa_subscriber.py` alongside QA HA — it writes mirrored states via REST
4. Start QA HA: `docker compose -f docker/qa/docker-compose.yml up`
5. Point MCP server at QA HA: `HA_URL=http://localhost:8124` (QA token)

### Entity allowlist
`BRIDGE_ENTITY_ALLOWLIST` in `.env` is a comma-separated list of entity IDs to sync:

```env
BRIDGE_ENTITY_ALLOWLIST=sensor.living_room_temperature,light.bedroom_main,binary_sensor.front_door
```

Start with a small allowlist of representative entities per domain you want to test. Expand as confidence grows.

---

## Prod environment

### What it is
The real Home Assistant instance managing the physical home. Agents are only granted access here after QA validation.

### Agent onboarding to prod (graduation process)
1. Agent validated in **Dev** — tool logic correct, no hallucinations on entity names
2. Agent validated in **QA** — correct decisions on real state data; command gate tested if applicable
3. Agent onboarded to prod in **read-only mode first** — observe behaviour for a period (days/weeks depending on risk)
4. Write access granted incrementally by domain — e.g. lights → climate → never locks without extra gates
5. Human confirmation gate (Phase 2) active for all agent-initiated service calls

### MCP server scoping in prod
Agents in prod should use the narrowest scope possible — only the entities and domains they need. This limits blast radius if an agent misbehaves and keeps tool lists small (less context consumed per call).

```env
# Example: a bedroom agent in prod
HA_SCOPE_AREAS=bedroom
HA_SCOPE_DOMAINS=light,sensor,climate
```

---

## Environment promotion checklist

Before promoting an agent from QA to prod:

- [ ] Agent has been running in QA for at least N sessions without unexpected tool calls
- [ ] All service calls attempted in QA were reviewed and deemed correct
- [ ] Prod MCP server scope is configured to the minimum required entities
- [ ] Human confirmation gate is configured (Phase 2) — or agent is read-only
- [ ] Rollback plan documented: which tools to revoke if agent misbehaves
