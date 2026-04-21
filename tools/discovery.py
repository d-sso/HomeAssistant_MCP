from __future__ import annotations
from ha_client import HAClient, paginate

_client: HAClient | None = None


def init(client: HAClient) -> None:
    global _client
    _client = client


async def _entity_registry() -> list[dict]:
    try:
        return await _client.get("/api/config/entity_registry/entries")
    except Exception:
        return await _client.get("/api/config/entity_registry")


async def _area_registry() -> list[dict]:
    try:
        return await _client.get("/api/config/area_registry/list")
    except Exception:
        return []


async def _floor_registry() -> list[dict]:
    try:
        return await _client.get("/api/config/floor_registry/list")
    except Exception:
        return []


async def _label_registry() -> list[dict]:
    try:
        return await _client.get("/api/config/label_registry/list")
    except Exception:
        return []


async def _device_registry() -> list[dict]:
    try:
        return await _client.get("/api/config/device_registry/list")
    except Exception:
        return []


def _build_area_floor_map(areas: list[dict]) -> dict[str, str | None]:
    """Map area_id -> floor_id."""
    return {a["area_id"]: a.get("floor_id") for a in areas}


async def list_entities(
    domain: str | None = None,
    area: str | None = None,
    floor: str | None = None,
    label: str | None = None,
    search: str | None = None,
    page: int = 1,
    page_size: int = 50,
) -> dict:
    """List Home Assistant entities with optional filtering.

    Args:
        domain: Filter by entity domain (e.g. 'light', 'sensor').
        area: Filter by area name or area_id.
        floor: Filter by floor name or floor_id.
        label: Filter by label name or label_id.
        search: Case-insensitive substring match on entity_id or friendly_name.
        page: Page number (1-indexed).
        page_size: Results per page (default 50).
    """
    entries = await _entity_registry()
    areas = await _area_registry()
    floors = await _floor_registry()

    area_floor_map = _build_area_floor_map(areas)
    area_name_map = {a.get("name", "").lower(): a["area_id"] for a in areas}
    floor_name_map = {f.get("name", "").lower(): f["floor_id"] for f in floors}

    resolved_area_id = area_name_map.get(area.lower()) if area else None
    if area and not resolved_area_id:
        resolved_area_id = area

    resolved_floor_id = floor_name_map.get(floor.lower()) if floor else None
    if floor and not resolved_floor_id:
        resolved_floor_id = floor

    results = []
    for entry in entries:
        if entry.get("disabled_by"):
            continue

        entity_id = entry.get("entity_id", "")
        entry_domain = entity_id.split(".")[0] if "." in entity_id else ""

        if domain and entry_domain != domain:
            continue
        if resolved_area_id and entry.get("area_id") != resolved_area_id:
            continue
        if resolved_floor_id:
            entry_floor = area_floor_map.get(entry.get("area_id", ""))
            if entry_floor != resolved_floor_id:
                continue
        if label:
            entry_labels = entry.get("labels") or []
            if label not in entry_labels:
                continue
        if search:
            search_lower = search.lower()
            name = (entry.get("name") or entry.get("original_name") or "").lower()
            if search_lower not in entity_id.lower() and search_lower not in name:
                continue

        results.append({
            "entity_id": entity_id,
            "name": entry.get("name") or entry.get("original_name"),
            "domain": entry_domain,
            "platform": entry.get("platform"),
            "area_id": entry.get("area_id"),
            "device_id": entry.get("device_id"),
            "labels": entry.get("labels") or [],
        })

    results = _client.scope_filter(results)
    return paginate(results, page, page_size)


async def list_devices(
    area: str | None = None,
    page: int = 1,
    page_size: int = 50,
) -> dict:
    """List Home Assistant devices, optionally filtered by area.

    Args:
        area: Filter by area name or area_id.
        page: Page number (1-indexed).
        page_size: Results per page (default 50).
    """
    devices = await _device_registry()
    areas = await _area_registry()
    area_name_map = {a.get("name", "").lower(): a["area_id"] for a in areas}

    resolved_area_id = area_name_map.get(area.lower()) if area else None
    if area and not resolved_area_id:
        resolved_area_id = area

    results = []
    for device in devices:
        if device.get("disabled_by"):
            continue
        if resolved_area_id and device.get("area_id") != resolved_area_id:
            continue
        results.append({
            "device_id": device.get("id"),
            "name": device.get("name") or device.get("name_by_user"),
            "manufacturer": device.get("manufacturer"),
            "model": device.get("model"),
            "area_id": device.get("area_id"),
        })

    return paginate(results, page, page_size)


async def list_areas() -> list[dict]:
    """List all areas (rooms) defined in Home Assistant."""
    areas = await _area_registry()
    return [
        {
            "area_id": a.get("area_id"),
            "name": a.get("name"),
            "floor_id": a.get("floor_id"),
        }
        for a in areas
    ]


async def list_floors() -> list[dict]:
    """List all floors defined in Home Assistant (requires HA 2024+)."""
    floors = await _floor_registry()
    return [
        {
            "floor_id": f.get("floor_id"),
            "name": f.get("name"),
            "level": f.get("level"),
        }
        for f in floors
    ]


async def list_labels() -> list[dict]:
    """List all labels defined in Home Assistant (requires HA 2023.3+)."""
    labels = await _label_registry()
    return [
        {
            "label_id": lbl.get("label_id"),
            "name": lbl.get("name"),
            "color": lbl.get("color"),
        }
        for lbl in labels
    ]


async def list_domains() -> list[str]:
    """List all active entity domains (e.g. light, sensor, switch)."""
    states = await _client.get("/api/states")
    domains: set[str] = set()
    for state in states:
        entity_id = state.get("entity_id", "")
        if "." in entity_id:
            domains.add(entity_id.split(".")[0])
    return sorted(domains)
