import pytest
from unittest.mock import AsyncMock, patch
from config import Config
from ha_client import HAClient
import tools.history as history_module

MOCK_HISTORY = [
    [
        {"entity_id": "sensor.temp", "state": "20.0", "last_changed": "2024-01-01T00:00:00+00:00"},
        {"entity_id": "sensor.temp", "state": "21.5", "last_changed": "2024-01-01T01:00:00+00:00"},
    ]
]

MOCK_LOGBOOK = [
    {"name": "Bedroom Light", "message": "turned on", "entity_id": "light.bedroom",
     "when": "2024-01-01T08:00:00+00:00"},
]


@pytest.fixture(autouse=True)
def setup_client():
    cfg = Config(ha_url="http://ha.test", ha_token="t")
    history_module.init(HAClient(cfg))


@pytest.mark.asyncio
async def test_get_history_returns_first_list():
    with patch.object(history_module._client, "get", new_callable=AsyncMock) as mock:
        mock.return_value = MOCK_HISTORY
        result = await history_module.get_history("sensor.temp", "2024-01-01T00:00:00+00:00")
        assert len(result) == 2
        assert result[0]["state"] == "20.0"


@pytest.mark.asyncio
async def test_get_history_empty_response():
    with patch.object(history_module._client, "get", new_callable=AsyncMock) as mock:
        mock.return_value = []
        result = await history_module.get_history("sensor.temp", "2024-01-01T00:00:00+00:00")
        assert result == []


@pytest.mark.asyncio
async def test_get_logbook():
    with patch.object(history_module._client, "get", new_callable=AsyncMock) as mock:
        mock.return_value = MOCK_LOGBOOK
        result = await history_module.get_logbook("2024-01-01T00:00:00+00:00")
        assert len(result) == 1
        assert result[0]["entity_id"] == "light.bedroom"


@pytest.mark.asyncio
async def test_get_history_passes_params():
    with patch.object(history_module._client, "get", new_callable=AsyncMock) as mock:
        mock.return_value = MOCK_HISTORY
        await history_module.get_history(
            "sensor.temp",
            "2024-01-01T00:00:00+00:00",
            end_time="2024-01-02T00:00:00+00:00",
        )
        _, kwargs = mock.call_args
        params = kwargs.get("params") or mock.call_args[0][1]
        assert params["filter_entity_id"] == "sensor.temp"
        assert params["end_time"] == "2024-01-02T00:00:00+00:00"
