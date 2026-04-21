from __future__ import annotations
from ha_client import HAClient, paginate

_client: HAClient | None = None


def init(client: HAClient) -> None:
    global _client
    _client = client


async def get_state(entity_id: str) -> dict:
    """Get the current state and attributes of a single entity.

    Args:
        entity_id: The entity ID (e.g. 'light.living_room').
    """
    return await _client.get(f"/api/states/{entity_id}")


async def get_states(
    domain: str | None = None,
    area: str | None = None,
    label: str | None = None,
    page: int = 1,
    page_size: int = 50,
) -> dict:
    """Get current states for multiple entities with optional filtering.

    Area and label filters trigger an entity registry lookup to resolve
    which entities belong to the requested area/label.

    Args:
        domain: Filter by entity domain (e.g. 'light', 'sensor').
        area: Filter by area name or area_id.
        label: Filter by label name or label_id.
        page: Page number (1-indexed).
        page_size: Results per page (default 50).
    """
    states = await _client.get("/api/states")

    if area or label:
        registry = await _get_registry_index()
    else:
        registry = {}

    results = []
    for state in states:
        entity_id = state.get("entity_id", "")
        entity_domain = entity_id.split(".")[0] if "." in entity_id else ""

        if domain and entity_domain != domain:
            continue

        if area or label:
            reg_entry = registry.get(entity_id, {})
            if area and reg_entry.get("area_id") != area:
                continue
            if label:
                if label not in (reg_entry.get("labels") or []):
                    continue

        results.append(state)

    results = _client.scope_filter(results)
    return paginate(results, page, page_size)


async def get_unavailable_entities() -> list[dict]:
    """Return all entities currently in an unavailable or unknown state."""
    states = await _client.get("/api/states")
    return [
        {"entity_id": s["entity_id"], "state": s["state"]}
        for s in states
        if s.get("state") in ("unavailable", "unknown")
    ]


async def _get_registry_index() -> dict[str, dict]:
    """Build a dict of entity_id -> {area_id, labels} from the entity registry."""
    try:
        entries = await _client.get("/api/config/entity_registry/entries")
    except Exception:
        try:
            entries = await _client.get("/api/config/entity_registry")
        except Exception:
            return {}
    return {
        e["entity_id"]: {"area_id": e.get("area_id"), "labels": e.get("labels") or []}
        for e in entries
        if "entity_id" in e
    }
