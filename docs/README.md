# HomeAssistant MCP Server

An MCP server exposing Home Assistant data as tools for Claude Code and other agents.

## Prerequisites

- Python 3.11+
- A running Home Assistant instance
- A long-lived access token from HA (`Profile → Security → Long-lived access tokens`)

## Installation

```bash
pip install -r requirements.txt
```

Create a `.env` file at the project root:

```env
HA_URL=http://homeassistant.local:8123
HA_TOKEN=your_long_lived_token_here
```

## Running the server

```bash
python server.py
```

The server communicates over stdio (default for Claude Code MCP integration).

---

## Wiring into Claude Code

Add entries to `~/.claude/settings.json` under `mcpServers`.

### Global instance (all entities)

```json
{
  "mcpServers": {
    "ha-global": {
      "command": "python",
      "args": ["C:/path/to/HomeAssistant/server.py"],
      "env": {
        "HA_URL": "http://homeassistant.local:8123",
        "HA_TOKEN": "your_token_here"
      }
    }
  }
}
```

### Scoped instances (per area/room)

Use the same server binary with different `HA_SCOPE_*` env vars. Each named entry becomes a separate tool namespace in Claude Code.

```json
{
  "mcpServers": {
    "ha-bedroom": {
      "command": "python",
      "args": ["C:/path/to/HomeAssistant/server.py"],
      "env": {
        "HA_URL": "http://homeassistant.local:8123",
        "HA_TOKEN": "your_token_here",
        "HA_SCOPE_AREAS": "bedroom"
      }
    },
    "ha-living-room": {
      "command": "python",
      "args": ["C:/path/to/HomeAssistant/server.py"],
      "env": {
        "HA_URL": "http://homeassistant.local:8123",
        "HA_TOKEN": "your_token_here",
        "HA_SCOPE_AREAS": "living_room"
      }
    },
    "ha-energy": {
      "command": "python",
      "args": ["C:/path/to/HomeAssistant/server.py"],
      "env": {
        "HA_URL": "http://homeassistant.local:8123",
        "HA_TOKEN": "your_token_here",
        "HA_SCOPE_DOMAINS": "sensor,energy"
      }
    }
  }
}
```

---

## Scope configuration reference

All scope variables accept comma-separated values.

| Environment variable | Filters by | Example |
|---|---|---|
| `HA_SCOPE_AREAS` | Area name(s) | `bedroom,office` |
| `HA_SCOPE_FLOORS` | Floor name(s) | `ground_floor` |
| `HA_SCOPE_DOMAINS` | Entity domain(s) | `light,switch,sensor` |
| `HA_SCOPE_LABELS` | HA label(s) | `energy_monitoring` |

Scope variables are combinable. Multiple variables are ANDed together (an entity must match all specified scopes to be included).

When no scope variables are set, all entities are accessible.

---

## Running multiple scoped agents

Each `mcpServers` entry is an independent server process. You can run as many as needed simultaneously — they share no state and do not interfere with each other. Assign each agent in Claude Code to a specific named MCP server to limit its view to the relevant entities.
