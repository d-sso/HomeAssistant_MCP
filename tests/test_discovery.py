import pytest
from unittest.mock import AsyncMock, patch
from config import Config
from ha_client import HAClient
import tools.discovery as discovery_module

MOCK_REGISTRY = [
    {"entity_id": "light.bedroom", "name": "Bedroom Light", "platform": "zha",
     "area_id": "bedroom", "device_id": "d1", "labels": [], "disabled_by": None},
    {"entity_id": "sensor.temp", "name": "Temperature", "platform": "zha",
     "area_id": "living_room", "device_id": "d2", "labels": ["energy"], "disabled_by": None},
    {"entity_id": "switch.disabled", "name": None, "platform": "zha",
     "area_id": None, "device_id": "d3", "labels": [], "disabled_by": "user"},
]

MOCK_AREAS = [
    {"area_id": "bedroom", "name": "Bedroom", "floor_id": "ground"},
    {"area_id": "living_room", "name": "Living Room", "floor_id": "ground"},
]


@pytest.fixture(autouse=True)
def setup_client():
    cfg = Config(ha_url="http://ha.test", ha_token="t")
    discovery_module.init(HAClient(cfg))


@pytest.fixture
def mock_registry():
    with patch.object(discovery_module, "_entity_registry", new_callable=AsyncMock) as r, \
         patch.object(discovery_module, "_area_registry", new_callable=AsyncMock) as a, \
         patch.object(discovery_module, "_floor_registry", new_callable=AsyncMock) as f:
        r.return_value = MOCK_REGISTRY
        a.return_value = MOCK_AREAS
        f.return_value = []
        yield


@pytest.mark.asyncio
async def test_list_entities_excludes_disabled(mock_registry):
    result = await discovery_module.list_entities()
    entity_ids = [e["entity_id"] for e in result["items"]]
    assert "switch.disabled" not in entity_ids


@pytest.mark.asyncio
async def test_list_entities_domain_filter(mock_registry):
    result = await discovery_module.list_entities(domain="light")
    assert result["total"] == 1
    assert result["items"][0]["entity_id"] == "light.bedroom"


@pytest.mark.asyncio
async def test_list_entities_area_filter(mock_registry):
    result = await discovery_module.list_entities(area="bedroom")
    assert result["total"] == 1
    assert result["items"][0]["entity_id"] == "light.bedroom"


@pytest.mark.asyncio
async def test_list_entities_label_filter(mock_registry):
    result = await discovery_module.list_entities(label="energy")
    assert result["total"] == 1
    assert result["items"][0]["entity_id"] == "sensor.temp"


@pytest.mark.asyncio
async def test_list_entities_search(mock_registry):
    result = await discovery_module.list_entities(search="bedroom")
    assert result["total"] == 1


@pytest.mark.asyncio
async def test_list_areas(mock_registry):
    result = await discovery_module.list_areas()
    names = [a["name"] for a in result]
    assert "Bedroom" in names
    assert "Living Room" in names
