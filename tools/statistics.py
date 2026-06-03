from __future__ import annotations
from ha_client import HAClient

_client: HAClient | None = None

VALID_PERIODS = {"5minute", "hour", "day", "week", "month"}
VALID_TYPES = {"mean", "min", "max", "sum", "state", "change"}


def init(client: HAClient) -> None:
    global _client
    _client = client


async def list_statistic_ids(statistic_type: str | None = None) -> list[dict]:
    """List entities that have long-term statistics available.

    Args:
        statistic_type: Optional filter — 'mean' (gauges like temperature) or
            'sum' (accumulating totals like energy).
    """
    payload: dict = {}
    if statistic_type:
        payload["statistic_type"] = statistic_type

    entries = await _client.ws_command("recorder/list_statistic_ids", **payload)

    # For recorder-sourced statistics the statistic_id IS the entity_id, so we
    # annotate it to let the configured scope filter apply (hard server-side).
    for entry in entries:
        entry.setdefault("entity_id", entry.get("statistic_id"))

    return _client.scope_filter(entries)


async def get_statistics(
    entity_id: str,
    start_time: str,
    end_time: str | None = None,
    period: str = "hour",
    types: list[str] | None = None,
) -> dict:
    """Query long-term statistics rollups for an entity over a time range.

    Args:
        entity_id: The statistic/entity ID to query (e.g. 'sensor.energy').
        start_time: ISO 8601 start datetime (e.g. '2024-01-01T00:00:00+00:00').
        end_time: ISO 8601 end datetime. Defaults to now.
        period: Rollup granularity — one of 5minute, hour, day, week, month.
        types: Which aggregates to return (mean, min, max, sum, state, change).
            Defaults to all available for the statistic.

    Returns a dict keyed by statistic_id, each value a list of rollup points
    with 'start'/'end' bounds and the requested aggregate fields.
    """
    if period not in VALID_PERIODS:
        raise ValueError(f"period must be one of {sorted(VALID_PERIODS)}, got '{period}'")
    if types:
        invalid = [t for t in types if t not in VALID_TYPES]
        if invalid:
            raise ValueError(f"invalid types {invalid}; valid: {sorted(VALID_TYPES)}")

    payload: dict = {
        "start_time": start_time,
        "statistic_ids": [entity_id],
        "period": period,
    }
    if end_time:
        payload["end_time"] = end_time
    if types:
        payload["types"] = types

    return await _client.ws_command("recorder/statistics_during_period", **payload)
