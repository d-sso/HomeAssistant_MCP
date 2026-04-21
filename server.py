import json
from mcp.server.fastmcp import FastMCP
from config import load_config
from ha_client import HAClient
import tools.discovery as discovery
import tools.states as states
import tools.history as history
import tools.config_tools as config_tools

config = load_config()
client = HAClient(config)

discovery.init(client)
states.init(client)
history.init(client)
config_tools.init(client)

mcp = FastMCP("homeassistant-mcp")


# ── Discovery ────────────────────────────────────────────────────────────────

@mcp.tool()
async def list_entities(
    domain: str | None = None,
    area: str | None = None,
    floor: str | None = None,
    label: str | None = None,
    search: str | None = None,
    page: int = 1,
    page_size: int = 50,
) -> str:
    """List Home Assistant entities with optional filtering by domain, area, floor, label, or search string."""
    result = await discovery.list_entities(domain, area, floor, label, search, page, page_size)
    return json.dumps(result, default=str)


@mcp.tool()
async def list_devices(
    area: str | None = None,
    page: int = 1,
    page_size: int = 50,
) -> str:
    """List physical devices registered in Home Assistant, optionally filtered by area."""
    result = await discovery.list_devices(area, page, page_size)
    return json.dumps(result, default=str)


@mcp.tool()
async def list_areas() -> str:
    """List all areas (rooms) defined in Home Assistant."""
    result = await discovery.list_areas()
    return json.dumps(result, default=str)


@mcp.tool()
async def list_floors() -> str:
    """List all floors defined in Home Assistant (requires HA 2024+)."""
    result = await discovery.list_floors()
    return json.dumps(result, default=str)


@mcp.tool()
async def list_labels() -> str:
    """List all labels defined in Home Assistant (requires HA 2023.3+)."""
    result = await discovery.list_labels()
    return json.dumps(result, default=str)


@mcp.tool()
async def list_domains() -> str:
    """List all active entity domains present in Home Assistant (e.g. light, sensor, switch)."""
    result = await discovery.list_domains()
    return json.dumps(result, default=str)


# ── States ────────────────────────────────────────────────────────────────────

@mcp.tool()
async def get_state(entity_id: str) -> str:
    """Get the current state and full attributes of a single Home Assistant entity."""
    result = await states.get_state(entity_id)
    return json.dumps(result, default=str)


@mcp.tool()
async def get_states(
    domain: str | None = None,
    area: str | None = None,
    label: str | None = None,
    page: int = 1,
    page_size: int = 50,
) -> str:
    """Get current states for multiple entities, optionally filtered by domain, area, or label."""
    result = await states.get_states(domain, area, label, page, page_size)
    return json.dumps(result, default=str)


@mcp.tool()
async def get_unavailable_entities() -> str:
    """Return all entities currently in an unavailable or unknown state."""
    result = await states.get_unavailable_entities()
    return json.dumps(result, default=str)


# ── History ───────────────────────────────────────────────────────────────────

@mcp.tool()
async def get_history(
    entity_id: str,
    start_time: str,
    end_time: str | None = None,
    minimal_response: bool = True,
) -> str:
    """Get the state change history for an entity.

    start_time and end_time must be ISO 8601 strings (e.g. '2024-01-01T00:00:00+00:00').
    """
    result = await history.get_history(entity_id, start_time, end_time, minimal_response)
    return json.dumps(result, default=str)


@mcp.tool()
async def get_logbook(
    start_time: str,
    end_time: str | None = None,
    entity_id: str | None = None,
) -> str:
    """Get human-readable logbook entries describing what happened and what triggered it.

    start_time and end_time must be ISO 8601 strings.
    """
    result = await history.get_logbook(start_time, end_time, entity_id)
    return json.dumps(result, default=str)


# ── Configuration & Context ────────────────────────────────────────────────────

@mcp.tool()
async def get_ha_config() -> str:
    """Get Home Assistant configuration: location, timezone, unit system, and version."""
    result = await config_tools.get_ha_config()
    return json.dumps(result, default=str)


@mcp.tool()
async def get_zones() -> str:
    """Get all configured geographic zones (home, work, and any custom zones)."""
    result = await config_tools.get_zones()
    return json.dumps(result, default=str)


@mcp.tool()
async def render_template(template: str) -> str:
    """Render a Jinja2 template using the Home Assistant template engine.

    Useful for computed queries across multiple entities. Example:
    '{{ states.sensor | selectattr(\"state\", \"!=\", \"unavailable\") | list | count }}'
    """
    return await config_tools.render_template(template)


@mcp.tool()
async def get_calendars() -> str:
    """List all calendar entities available in Home Assistant."""
    result = await config_tools.get_calendars()
    return json.dumps(result, default=str)


@mcp.tool()
async def get_calendar_events(
    entity_id: str,
    start_time: str,
    end_time: str,
) -> str:
    """Get events from a calendar entity within a time range.

    start_time and end_time must be ISO 8601 strings.
    """
    result = await config_tools.get_calendar_events(entity_id, start_time, end_time)
    return json.dumps(result, default=str)


if __name__ == "__main__":
    mcp.run()
