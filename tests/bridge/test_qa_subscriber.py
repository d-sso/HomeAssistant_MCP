import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from config import Config
from bridge.qa_subscriber import QASubscriber


@pytest.fixture
def config():
    return Config(ha_url="http://qa-ha.test:8123", ha_token="qa-token")


@pytest.fixture
def subscriber(config):
    return QASubscriber(config)


@pytest.mark.asyncio
async def test_handle_message_with_entity_id_in_payload(subscriber):
    payload = json.dumps({
        "entity_id": "light.bedroom",
        "state": "on",
        "attributes": {"brightness": 200},
    }).encode()

    msg = MagicMock()
    msg.topic = "ha/states/light.bedroom"
    msg.payload = payload

    with patch("bridge.qa_subscriber.httpx.AsyncClient") as mock_client_cls:
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_http = AsyncMock()
        mock_http.__aenter__ = AsyncMock(return_value=mock_http)
        mock_http.__aexit__ = AsyncMock(return_value=False)
        mock_http.post = AsyncMock(return_value=mock_response)
        mock_client_cls.return_value = mock_http

        await subscriber._handle_message(msg)

        mock_http.post.assert_called_once()
        call_kwargs = mock_http.post.call_args
        assert "light.bedroom" in call_kwargs[0][0]
        body = call_kwargs[1]["json"]
        assert body["state"] == "on"


@pytest.mark.asyncio
async def test_handle_message_derives_entity_id_from_topic(subscriber):
    payload = json.dumps({"state": "off", "attributes": {}}).encode()

    msg = MagicMock()
    msg.topic = "ha/states/switch.garden"
    msg.payload = payload

    with patch("bridge.qa_subscriber.httpx.AsyncClient") as mock_client_cls:
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_http = AsyncMock()
        mock_http.__aenter__ = AsyncMock(return_value=mock_http)
        mock_http.__aexit__ = AsyncMock(return_value=False)
        mock_http.post = AsyncMock(return_value=mock_response)
        mock_client_cls.return_value = mock_http

        await subscriber._handle_message(msg)

        url = mock_http.post.call_args[0][0]
        assert "switch.garden" in url


@pytest.mark.asyncio
async def test_handle_message_invalid_json_does_not_raise(subscriber):
    msg = MagicMock()
    msg.topic = "ha/states/light.x"
    msg.payload = b"not-json"
    await subscriber._handle_message(msg)
