import pytest
from unittest.mock import AsyncMock, patch
from config import Config
from ha_client import HAClient
import tools.states as states_module

MOCK_STATES = [
    {"entity_id": "light.bedroom", "state": "on", "attributes": {"brightness": 255}},
    {"entity_id": "sensor.temperature", "state": "21.5", "attributes": {}},
    {"entity_id": "switch.garden", "state": "unavailable", "attributes": {}},
]


@pytest.fixture(autouse=True)
def setup_client():
    cfg = Config(ha_url="http://ha.test", ha_token="t")
    states_module.init(HAClient(cfg))


@pytest.fixture
def mock_get_states():
    with patch.object(states_module._client, "get", new_callable=AsyncMock) as mock:
        mock.return_value = MOCK_STATES
        yield mock


@pytest.mark.asyncio
async def test_get_state_calls_correct_endpoint():
    with patch.object(states_module._client, "get", new_callable=AsyncMock) as mock:
        mock.return_value = MOCK_STATES[0]
        result = await states_module.get_state("light.bedroom")
        mock.assert_called_once_with("/api/states/light.bedroom")
        assert result["state"] == "on"


@pytest.mark.asyncio
async def test_get_states_no_filter_returns_all(mock_get_states):
    result = await states_module.get_states()
    assert result["total"] == 3


@pytest.mark.asyncio
async def test_get_states_domain_filter(mock_get_states):
    result = await states_module.get_states(domain="light")
    assert result["total"] == 1
    assert result["items"][0]["entity_id"] == "light.bedroom"


@pytest.mark.asyncio
async def test_get_unavailable_entities(mock_get_states):
    result = await states_module.get_unavailable_entities()
    assert len(result) == 1
    assert result[0]["entity_id"] == "switch.garden"
    assert result[0]["state"] == "unavailable"
