"""Prod-side bridge: watches HA state changes via WebSocket and publishes to MQTT.

Run on or near the production HA host:
    python -m bridge.prod_publisher

Requires BRIDGE_ENTITY_ALLOWLIST to be set — only listed entities are published.
"""
import asyncio
import json
import logging
import signal
import sys
import paho.mqtt.client as mqtt
import websockets
from config import load_config

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

_shutdown = asyncio.Event()


def _build_mqtt_client(config) -> mqtt.Client:
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    if config.mqtt_username:
        client.username_pw_set(config.mqtt_username, config.mqtt_password)
    client.connect(config.mqtt_host, config.mqtt_port, keepalive=60)
    client.loop_start()
    return client


async def _ha_websocket_url(ha_url: str) -> str:
    base = ha_url.replace("https://", "wss://").replace("http://", "ws://")
    return f"{base}/api/websocket"


async def run(config) -> None:
    if not config.bridge_entity_allowlist:
        log.error("BRIDGE_ENTITY_ALLOWLIST is empty — nothing to publish. Exiting.")
        return

    allowlist = set(config.bridge_entity_allowlist)
    mqtt_client = _build_mqtt_client(config)
    ws_url = await _ha_websocket_url(config.ha_url)

    log.info("Connecting to HA WebSocket at %s", ws_url)
    log.info("Watching %d entities", len(allowlist))

    async with websockets.connect(ws_url) as ws:
        # HA auth handshake
        auth_required = json.loads(await ws.recv())
        assert auth_required["type"] == "auth_required", f"Unexpected: {auth_required}"

        await ws.send(json.dumps({"type": "auth", "access_token": config.ha_token}))
        auth_result = json.loads(await ws.recv())
        if auth_result["type"] != "auth_ok":
            log.error("HA auth failed: %s", auth_result)
            return
        log.info("HA WebSocket authenticated")

        # Subscribe to state_changed events
        await ws.send(json.dumps({"id": 1, "type": "subscribe_events", "event_type": "state_changed"}))
        sub_result = json.loads(await ws.recv())
        if not sub_result.get("success"):
            log.error("Failed to subscribe to state_changed: %s", sub_result)
            return
        log.info("Subscribed to state_changed events")

        while not _shutdown.is_set():
            try:
                raw = await asyncio.wait_for(ws.recv(), timeout=30.0)
            except asyncio.TimeoutError:
                continue
            except websockets.ConnectionClosed:
                log.warning("WebSocket connection closed — reconnecting in 5s")
                await asyncio.sleep(5)
                break

            msg = json.loads(raw)
            if msg.get("type") != "event":
                continue

            event_data = msg.get("event", {}).get("data", {})
            entity_id = event_data.get("entity_id", "")

            if entity_id not in allowlist:
                continue

            new_state = event_data.get("new_state")
            if not new_state:
                continue

            topic = f"{config.mqtt_topic_prefix}/states/{entity_id}"
            payload = json.dumps(new_state, default=str)
            mqtt_client.publish(topic, payload, retain=True)
            log.debug("Published %s → %s", entity_id, new_state.get("state"))

    mqtt_client.loop_stop()
    mqtt_client.disconnect()


def _handle_signal(*_):
    log.info("Shutdown signal received")
    _shutdown.set()


if __name__ == "__main__":
    cfg = load_config()

    loop = asyncio.new_event_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, _handle_signal)

    try:
        loop.run_until_complete(run(cfg))
    except KeyboardInterrupt:
        pass
    finally:
        loop.close()
        sys.exit(0)
