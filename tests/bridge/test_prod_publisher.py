import pytest
from config import Config
from bridge.prod_publisher import _ha_websocket_url


@pytest.mark.asyncio
async def test_websocket_url_http():
    url = await _ha_websocket_url("http://homeassistant.local:8123")
    assert url == "ws://homeassistant.local:8123/api/websocket"


@pytest.mark.asyncio
async def test_websocket_url_https():
    url = await _ha_websocket_url("https://homeassistant.local:8123")
    assert url == "wss://homeassistant.local:8123/api/websocket"


def test_empty_allowlist_is_detectable():
    cfg = Config(ha_url="http://ha.test", ha_token="t", bridge_entity_allowlist=[])
    assert len(cfg.bridge_entity_allowlist) == 0


def test_allowlist_populated():
    cfg = Config(
        ha_url="http://ha.test",
        ha_token="t",
        bridge_entity_allowlist=["light.bedroom", "sensor.temp"],
    )
    assert "light.bedroom" in cfg.bridge_entity_allowlist
