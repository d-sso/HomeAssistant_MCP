import pytest
import respx
import httpx
from config import Config
from ha_client import HAClient, paginate


@pytest.fixture
def config():
    return Config(ha_url="http://ha.test:8123", ha_token="test-token")


@pytest.fixture
def client(config):
    return HAClient(config)


# ── paginate ──────────────────────────────────────────────────────────────────

def test_paginate_first_page():
    items = list(range(10))
    result = paginate(items, page=1, page_size=3)
    assert result["items"] == [0, 1, 2]
    assert result["total"] == 10
    assert result["pages"] == 4
    assert result["page"] == 1


def test_paginate_last_page():
    items = list(range(10))
    result = paginate(items, page=4, page_size=3)
    assert result["items"] == [9]


def test_paginate_empty():
    result = paginate([], page=1, page_size=50)
    assert result["items"] == []
    assert result["total"] == 0
    assert result["pages"] == 1


# ── scope_filter ──────────────────────────────────────────────────────────────

def test_scope_filter_no_scope_returns_all(config, client):
    entities = [{"entity_id": "light.a"}, {"entity_id": "sensor.b"}]
    assert client.scope_filter(entities) == entities


def test_scope_filter_by_domain():
    cfg = Config(ha_url="http://x", ha_token="t", scope_domains=["light"])
    c = HAClient(cfg)
    entities = [{"entity_id": "light.a"}, {"entity_id": "sensor.b"}]
    assert c.scope_filter(entities) == [{"entity_id": "light.a"}]


def test_scope_filter_by_area():
    cfg = Config(ha_url="http://x", ha_token="t", scope_areas=["bedroom"])
    c = HAClient(cfg)
    entities = [
        {"entity_id": "light.a", "area_id": "bedroom"},
        {"entity_id": "light.b", "area_id": "living_room"},
    ]
    assert c.scope_filter(entities) == [{"entity_id": "light.a", "area_id": "bedroom"}]


def test_scope_filter_by_label():
    cfg = Config(ha_url="http://x", ha_token="t", scope_labels=["energy"])
    c = HAClient(cfg)
    entities = [
        {"entity_id": "sensor.a", "labels": ["energy"]},
        {"entity_id": "sensor.b", "labels": []},
    ]
    assert c.scope_filter(entities) == [{"entity_id": "sensor.a", "labels": ["energy"]}]


# ── HTTP methods ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
@respx.mock
async def test_get_sets_auth_header(client):
    route = respx.get("http://ha.test:8123/api/states").mock(
        return_value=httpx.Response(200, json=[])
    )
    await client.get("/api/states")
    assert route.called
    request = route.calls[0].request
    assert request.headers["authorization"] == "Bearer test-token"


@pytest.mark.asyncio
@respx.mock
async def test_get_raises_on_error(client):
    respx.get("http://ha.test:8123/api/states").mock(
        return_value=httpx.Response(401, json={"message": "Unauthorized"})
    )
    with pytest.raises(httpx.HTTPStatusError):
        await client.get("/api/states")


@pytest.mark.asyncio
@respx.mock
async def test_post_sends_json_body(client):
    route = respx.post("http://ha.test:8123/api/template").mock(
        return_value=httpx.Response(200, text="25")
    )
    await client.post("/api/template", {"template": "{{ 25 }}"})
    assert route.called
    assert json_body(route) == {"template": "{{ 25 }}"}


def json_body(route) -> dict:
    import json
    return json.loads(route.calls[0].request.content)


# ── ws_command ──────────────────────────────────────────────────────────────

class _FakeWS:
    """Minimal async context manager mimicking a websockets connection.

    Pops queued server messages on recv() and records what the client sends.
    """

    def __init__(self, server_messages):
        self._incoming = [__import__("json").dumps(m) for m in server_messages]
        self.sent = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def recv(self):
        return self._incoming.pop(0)

    async def send(self, raw):
        self.sent.append(__import__("json").loads(raw))


def test_ws_url_derivation(config):
    assert HAClient(config)._ws_url() == "ws://ha.test:8123/api/websocket"
    secure = Config(ha_url="https://x.example.com", ha_token="t")
    assert HAClient(secure)._ws_url() == "wss://x.example.com/api/websocket"


@pytest.mark.asyncio
async def test_ws_command_auth_and_result(client, monkeypatch):
    fake = _FakeWS([
        {"type": "auth_required"},
        {"type": "auth_ok"},
        {"id": 1, "type": "result", "success": True, "result": [{"area_id": "bedroom"}]},
    ])
    monkeypatch.setattr("ha_client.websockets.connect", lambda *a, **k: fake)

    result = await client.ws_command("config/area_registry/list")

    assert result == [{"area_id": "bedroom"}]
    assert fake.sent[0] == {"type": "auth", "access_token": "test-token"}
    assert fake.sent[1] == {"id": 1, "type": "config/area_registry/list"}


@pytest.mark.asyncio
async def test_ws_command_raises_on_failure(client, monkeypatch):
    fake = _FakeWS([
        {"type": "auth_required"},
        {"type": "auth_ok"},
        {"id": 1, "type": "result", "success": False, "error": {"code": "unknown_command"}},
    ])
    monkeypatch.setattr("ha_client.websockets.connect", lambda *a, **k: fake)

    with pytest.raises(RuntimeError, match="unknown_command"):
        await client.ws_command("config/label_registry/list")
