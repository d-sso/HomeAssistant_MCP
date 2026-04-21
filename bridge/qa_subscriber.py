"""QA-side bridge: subscribes to MQTT state topics and mirrors them into QA HA via REST.

Run alongside the QA Home Assistant instance:
    python -m bridge.qa_subscriber

Subscribes to {MQTT_TOPIC_PREFIX}/states/# and writes each state to QA HA
using POST /api/states/<entity_id>.
"""
import asyncio
import json
import logging
import signal
import sys
import httpx
import paho.mqtt.client as mqtt
from config import load_config

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

_loop: asyncio.AbstractEventLoop | None = None
_shutdown = asyncio.Event()


class QASubscriber:
    def __init__(self, config):
        self._config = config
        self._headers = {
            "Authorization": f"Bearer {config.ha_token}",
            "Content-Type": "application/json",
        }

    def _on_connect(self, client, userdata, flags, reason_code, properties):
        if reason_code == 0:
            topic = f"{self._config.mqtt_topic_prefix}/states/#"
            client.subscribe(topic)
            log.info("Subscribed to %s", topic)
        else:
            log.error("MQTT connect failed: reason_code=%s", reason_code)

    def _on_message(self, client, userdata, msg):
        if _loop and not _loop.is_closed():
            asyncio.run_coroutine_threadsafe(self._handle_message(msg), _loop)

    async def _handle_message(self, msg):
        try:
            state_data = json.loads(msg.payload)
        except json.JSONDecodeError:
            log.warning("Invalid JSON on topic %s", msg.topic)
            return

        entity_id = state_data.get("entity_id")
        if not entity_id:
            # Derive from topic: {prefix}/states/<entity_id>
            parts = msg.topic.split("/", 2)
            entity_id = parts[2] if len(parts) == 3 else None

        if not entity_id:
            log.warning("Could not determine entity_id from topic %s", msg.topic)
            return

        payload = {
            "state": state_data.get("state"),
            "attributes": state_data.get("attributes", {}),
        }

        try:
            async with httpx.AsyncClient() as http:
                response = await http.post(
                    f"{self._config.ha_url}/api/states/{entity_id}",
                    headers=self._headers,
                    json=payload,
                    timeout=10.0,
                )
                response.raise_for_status()
                log.debug("Mirrored %s → %s", entity_id, payload["state"])
        except Exception as exc:
            log.error("Failed to mirror %s: %s", entity_id, exc)

    def build_mqtt_client(self) -> mqtt.Client:
        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        client.on_connect = self._on_connect
        client.on_message = self._on_message
        if self._config.mqtt_username:
            client.username_pw_set(self._config.mqtt_username, self._config.mqtt_password)
        return client


async def run(config) -> None:
    subscriber = QASubscriber(config)
    mqtt_client = subscriber.build_mqtt_client()
    mqtt_client.connect(config.mqtt_host, config.mqtt_port, keepalive=60)
    mqtt_client.loop_start()

    log.info("QA subscriber running — mirroring states to %s", config.ha_url)

    await _shutdown.wait()

    mqtt_client.loop_stop()
    mqtt_client.disconnect()
    log.info("QA subscriber stopped")


def _handle_signal(*_):
    log.info("Shutdown signal received")
    _shutdown.set()


if __name__ == "__main__":
    cfg = load_config()

    _loop = asyncio.new_event_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        _loop.add_signal_handler(sig, _handle_signal)

    try:
        _loop.run_until_complete(run(cfg))
    except KeyboardInterrupt:
        pass
    finally:
        _loop.close()
        sys.exit(0)
