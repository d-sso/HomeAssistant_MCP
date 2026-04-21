# Design Decisions

## Transport: MCP server over stdio

**Decision:** Expose HomeAssistant tools via an MCP (Model Context Protocol) server.

**Alternatives considered:**
- Raw Python scripts called directly — not agent-callable without per-agent wrappers
- Claude API tool definitions inline — must be redefined in every agent, no reuse
- FastAPI HTTP wrapper — works but adds an unnecessary HTTP layer; MCP is the standard

**Rationale:** MCP is natively supported by Claude Code and is becoming the standard tool protocol for AI agents. A single MCP server implementation works across Claude Code, the Anthropic SDK (with MCP client support), and any other MCP-compatible agent runtime. stdio transport avoids running a persistent HTTP service.

---

## Multi-agent context isolation via env-var scoping

**Decision:** A single server codebase supports multiple scoped deployments via `HA_SCOPE_*` environment variables. Each agent connects to its own named server instance configured with the appropriate scope.

**Alternatives considered:**
- Single server with a `set_context` tool — relies on the agent respecting its context; no enforcement
- Separate codebases per agent — maintenance overhead, drift risk
- Client-side tool allowlists only — coarse; doesn't filter data within a tool's response

**Rationale:** Environment-variable scoping gives hard server-side filtering with zero code duplication. Claude Code's `mcpServers` config makes it trivial to declare multiple named instances of the same binary with different env vars. Scope variables are ANDed so combinations (e.g. area + domain) are naturally composable.

---

## Read-only first, controls later

**Decision:** Phase 1 is strictly read-only. Control tools (service calls) are deferred to Phase 2, gated behind a human confirmation mechanism.

**Rationale:** Control actions are irreversible (lights, locks, thermostats). Exposing them to an agent without a confirmation step creates risk of unintended side effects. The confirmation architecture requires HA-side setup (see [architecture.md](architecture.md)) and deserves its own design pass before implementation.

---

## REST polling over WebSocket (Phase 1)

**Decision:** Phase 1 uses the HA REST API exclusively. WebSocket support is deferred.

**Rationale:** REST is stateless, simpler to implement, and sufficient for on-demand agent queries. WebSocket is needed for event-driven agent activation and for the bridge publisher — but both are Phase 3+ concerns. The bridge's `prod_publisher.py` will be the first user of WebSocket when the time comes.

---

## Near-term history first, long-term statistics deferred

**Decision:** Phase 1 includes `get_history` (raw state changes, HA recorder) but not long-term statistics (HA statistics tables).

**Rationale:** Near-term history covers the majority of conversational queries ("what happened in the last hour/day"). Long-term statistics use a different HA API endpoint, have a different data model (aggregates vs. raw events), and are the primary enabler for energy-efficiency analysis agents — a distinct use case that warrants its own phase.

---

## Template rendering exposed as a tool

**Decision:** `render_template` is included in Phase 1 despite being a control-adjacent capability.

**Rationale:** HA's Jinja2 template engine is read-only (it computes values, it doesn't change state) and is significantly more expressive than raw state queries. It allows an agent to ask computed questions ("what is the average temperature across all bedroom sensors?") without needing bespoke tool implementations for every aggregation pattern.

---

## Repo split: two repos, not three

**Decision:** Two repositories — `homeassistant-config` and `homeassistant-mcp` (this repo). The bridge service lives in `homeassistant-mcp` alongside the MCP server, not in a third repo.

**Alternatives considered:**
- Single monorepo — HA config changes (frequent, YAML) pollute Python service history
- Three repos (config / MCP server / bridge) — bridge and MCP server share `ha_client.py`, `config.py`, and entity models; splitting them forces code duplication or a shared library package

**Rationale:** The natural split is HA configuration vs. Python services that talk to HA. Bridge and MCP server are different processes and deployment targets but share meaningful code — keeping them in one repo avoids duplication without mixing concerns. The `homeassistant-config` repo is managed independently and referenced only in documentation here.

---

## QA state sync via MQTT bridge (not Zigbee2MQTT migration)

**Decision:** QA receives real entity states via a thin MQTT bridge (prod publishes, QA subscribes) rather than migrating the production HA device stack to Zigbee2MQTT.

**Alternatives considered:**
- Migrate prod to Zigbee2MQTT — cleaner long-term but a non-trivial one-time migration; also doesn't address the many non-Zigbee integrations (cloud services, WiFi devices) that feed prod HA
- Full prod replica with no live data — simpler but QA agents can't validate behavior against real states

**Rationale:** Prod has ZHA plus numerous other integrations; restructuring around MQTT as the primary device protocol would be a large migration with significant risk and limited benefit. The bridge approach keeps prod untouched, introduces no new device dependencies, and still provides QA with selective real-world state parity. The `BRIDGE_ENTITY_ALLOWLIST` is the mechanism for controlling exactly which entities flow through.
