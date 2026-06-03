import pytest
from unittest.mock import AsyncMock
from config import Config
from ha_client import HAClient
import tools.statistics as statistics


@pytest.fixture
def client():
    cfg = Config(ha_url="http://ha.test", ha_token="t")
    c = HAClient(cfg)
    c.ws_command = AsyncMock()
    statistics.init(c)
    return c


@pytest.mark.asyncio
async def test_list_statistic_ids_passes_type_filter(client):
    client.ws_command.return_value = [
        {"statistic_id": "sensor.energy", "has_sum": True, "statistics_unit_of_measurement": "kWh"},
    ]
    result = await statistics.list_statistic_ids(statistic_type="sum")

    client.ws_command.assert_awaited_once_with(
        "recorder/list_statistic_ids", statistic_type="sum"
    )
    # statistic_id is annotated as entity_id so scope filtering can apply
    assert result[0]["entity_id"] == "sensor.energy"


@pytest.mark.asyncio
async def test_list_statistic_ids_no_type(client):
    client.ws_command.return_value = []
    await statistics.list_statistic_ids()
    client.ws_command.assert_awaited_once_with("recorder/list_statistic_ids")


@pytest.mark.asyncio
async def test_list_statistic_ids_respects_scope(client):
    client._config.scope_domains = ["sensor"]
    client.ws_command.return_value = [
        {"statistic_id": "sensor.energy"},
        {"statistic_id": "light.kitchen"},
    ]
    result = await statistics.list_statistic_ids()
    ids = [e["statistic_id"] for e in result]
    assert ids == ["sensor.energy"]


@pytest.mark.asyncio
async def test_get_statistics_builds_command(client):
    client.ws_command.return_value = {"sensor.energy": [{"start": 0, "sum": 12.5}]}
    result = await statistics.get_statistics(
        "sensor.energy",
        start_time="2024-01-01T00:00:00+00:00",
        end_time="2024-02-01T00:00:00+00:00",
        period="day",
        types=["sum", "change"],
    )

    client.ws_command.assert_awaited_once_with(
        "recorder/statistics_during_period",
        start_time="2024-01-01T00:00:00+00:00",
        statistic_ids=["sensor.energy"],
        period="day",
        end_time="2024-02-01T00:00:00+00:00",
        types=["sum", "change"],
    )
    assert result == {"sensor.energy": [{"start": 0, "sum": 12.5}]}


@pytest.mark.asyncio
async def test_get_statistics_defaults_omit_optional_fields(client):
    client.ws_command.return_value = {}
    await statistics.get_statistics("sensor.temp", start_time="2024-01-01T00:00:00+00:00")
    client.ws_command.assert_awaited_once_with(
        "recorder/statistics_during_period",
        start_time="2024-01-01T00:00:00+00:00",
        statistic_ids=["sensor.temp"],
        period="hour",
    )


@pytest.mark.asyncio
async def test_get_statistics_rejects_bad_period(client):
    with pytest.raises(ValueError, match="period must be one of"):
        await statistics.get_statistics("sensor.x", "2024-01-01T00:00:00+00:00", period="yearly")


@pytest.mark.asyncio
async def test_get_statistics_rejects_bad_types(client):
    with pytest.raises(ValueError, match="invalid types"):
        await statistics.get_statistics(
            "sensor.x", "2024-01-01T00:00:00+00:00", types=["sum", "bogus"]
        )
