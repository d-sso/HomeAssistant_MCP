from __future__ import annotations
from ha_client import HAClient

_client: HAClient | None = None


def init(client: HAClient) -> None:
    global _client
    _client = client


async def get_history(
    entity_id: str,
    start_time: str,
    end_time: str | None = None,
    minimal_response: bool = True,
) -> list[dict]:
    """Get the state change history for an entity over a time range.

    Args:
        entity_id: The entity ID to query (e.g. 'sensor.temperature').
        start_time: ISO 8601 start datetime (e.g. '2024-01-01T00:00:00+00:00').
        end_time: ISO 8601 end datetime. Defaults to now.
        minimal_response: If True, omits unchanged attributes to reduce payload size.
    """
    params: dict = {"filter_entity_id": entity_id}
    if end_time:
        params["end_time"] = end_time
    if minimal_response:
        params["minimal_response"] = "true"

    result = await _client.get(f"/api/history/period/{start_time}", params=params)
    # HA returns a list of lists (one inner list per entity_id requested)
    return result[0] if result else []


async def get_logbook(
    start_time: str,
    end_time: str | None = None,
    entity_id: str | None = None,
) -> list[dict]:
    """Get human-readable logbook entries over a time range.

    The logbook describes what happened and what triggered it in plain language.

    Args:
        start_time: ISO 8601 start datetime.
        end_time: ISO 8601 end datetime. Defaults to now.
        entity_id: Optional — limit entries to a specific entity.
    """
    params: dict = {}
    if end_time:
        params["end_time"] = end_time
    if entity_id:
        params["entity"] = entity_id

    return await _client.get(f"/api/logbook/{start_time}", params=params)
