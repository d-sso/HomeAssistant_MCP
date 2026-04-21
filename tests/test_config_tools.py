import pytest
from unittest.mock import AsyncMock, patch
from config import Config
from ha_client import HAClient
import tools.config_tools as config_tools_module

MOCK_HA_CONFIG = {
    "location_name": "Home",
    "latitude": 51.5,
    "longitude": -0.1,
    "elevation": 10,
    "unit_system": {"length": "km", "temperature": "°C"},
    "time_zone": "Europe/London",
    "version": "2024.1.0",
    "components": ["light", "sensor"],
}

MOCK_STATES_WITH_ZONE = [
    {"entity_id": "zone.home", "state": "zoning",
     "attributes": {"friendly_name": "Home", "latitude": 51.5, "longitude": -0.1, "radius": 100, "passive": False}},
    {"entity_id": "light.bedroom", "state": "on", "attributes": {}},
]


@pytest.fixture(autouse=True)
def setup_client():
    cfg = Config(ha_url="http://ha.test", ha_token="t")
    config_tools_module.init(HAClient(cfg))


@pytest.mark.asyncio
async def test_get_ha_config_shape():
    with patch.object(config_tools_module._client, "get", new_callable=AsyncMock) as mock:
        mock.return_value = MOCK_HA_CONFIG
        result = await config_tools_module.get_ha_config()
        assert result["location_name"] == "Home"
        assert result["version"] == "2024.1.0"
        assert "components" in result


@pytest.mark.asyncio
async def test_get_zones_filters_only_zone_entities():
    with patch.object(config_tools_module._client, "get", new_callable=AsyncMock) as mock:
        mock.return_value = MOCK_STATES_WITH_ZONE
        result = await config_tools_module.get_zones()
        assert len(result) == 1
        assert result[0]["entity_id"] == "zone.home"


@pytest.mark.asyncio
async def test_render_template_returns_string():
    with patch.object(config_tools_module._client, "post", new_callable=AsyncMock) as mock:
        mock.return_value = "25"
        result = await config_tools_module.render_template("{{ 25 }}")
        assert result == "25"


@pytest.mark.asyncio
async def test_get_calendars():
    with patch.object(config_tools_module._client, "get", new_callable=AsyncMock) as mock:
        mock.return_value = [{"entity_id": "calendar.home", "name": "Home"}]
        result = await config_tools_module.get_calendars()
        assert result[0]["entity_id"] == "calendar.home"
