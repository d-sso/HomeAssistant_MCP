from __future__ import annotations
from ha_client import HAClient

_client: HAClient | None = None


def init(client: HAClient) -> None:
    global _client
    _client = client


async def get_ha_config() -> dict:
    """Get Home Assistant configuration: location, timezone, unit system, version."""
    raw = await _client.get("/api/config")
    return {
        "location_name": raw.get("location_name"),
        "latitude": raw.get("latitude"),
        "longitude": raw.get("longitude"),
        "elevation": raw.get("elevation"),
        "unit_system": raw.get("unit_system"),
        "time_zone": raw.get("time_zone"),
        "version": raw.get("version"),
        "components": raw.get("components", []),
    }


async def get_zones() -> list[dict]:
    """Get all configured zones (home, work, and any custom geographic zones)."""
    states = await _client.get("/api/states")
    zones = []
    for state in states:
        if not state.get("entity_id", "").startswith("zone."):
            continue
        attrs = state.get("attributes", {})
        zones.append({
            "entity_id": state["entity_id"],
            "name": attrs.get("friendly_name"),
            "latitude": attrs.get("latitude"),
            "longitude": attrs.get("longitude"),
            "radius": attrs.get("radius"),
            "passive": attrs.get("passive", False),
        })
    return zones


async def render_template(template: str) -> str:
    """Render a Jinja2 template using the Home Assistant template engine.

    Useful for computed queries, e.g.:
      '{{ states.sensor | selectattr(\"state\", \"!=\", \"unavailable\") | list | count }}'

    Args:
        template: A Jinja2 template string compatible with HA's template engine.
    """
    result = await _client.post("/api/template", {"template": template})
    if isinstance(result, dict):
        return result.get("result", str(result))
    return str(result)


async def get_calendars() -> list[dict]:
    """List all calendar entities available in Home Assistant."""
    calendars = await _client.get("/api/calendars")
    return [
        {
            "entity_id": cal.get("entity_id"),
            "name": cal.get("name"),
        }
        for cal in calendars
    ]


async def get_calendar_events(
    entity_id: str,
    start_time: str,
    end_time: str,
) -> list[dict]:
    """Get events from a calendar entity within a time range.

    Args:
        entity_id: The calendar entity ID (e.g. 'calendar.home').
        start_time: ISO 8601 start datetime.
        end_time: ISO 8601 end datetime.
    """
    events = await _client.get(
        f"/api/calendars/{entity_id}",
        params={"start": start_time, "end": end_time},
    )
    return [
        {
            "summary": e.get("summary"),
            "start": e.get("start"),
            "end": e.get("end"),
            "description": e.get("description"),
            "location": e.get("location"),
        }
        for e in events
    ]
