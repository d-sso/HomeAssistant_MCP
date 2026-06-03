import json
import httpx
import websockets
from typing import Any
from config import Config


def paginate(items: list, page: int, page_size: int) -> dict:
    total = len(items)
    start = (page - 1) * page_size
    end = start + page_size
    return {
        "items": items[start:end],
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": max(1, (total + page_size - 1) // page_size),
    }


class HAClient:
    def __init__(self, config: Config):
        self._config = config
        self._base_url = config.ha_url
        self._headers = {
            "Authorization": f"Bearer {config.ha_token}",
            "Content-Type": "application/json",
        }

    async def get(self, path: str, params: dict | None = None) -> Any:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self._base_url}{path}",
                headers=self._headers,
                params=params,
                timeout=30.0,
            )
            response.raise_for_status()
            return response.json()

    async def post(self, path: str, body: dict | None = None) -> Any:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self._base_url}{path}",
                headers=self._headers,
                json=body or {},
                timeout=30.0,
            )
            response.raise_for_status()
            return response.json()

    def _ws_url(self) -> str:
        base = self._base_url.replace("https://", "wss://").replace("http://", "ws://")
        return f"{base}/api/websocket"

    async def ws_command(self, command_type: str, **payload) -> Any:
        """Run a single command against the HA WebSocket API and return its result.

        Required for data the REST API does not expose — notably the entity,
        device, area, floor, and label registries (``config/*_registry/list``).
        Opens a short-lived connection, performs the HA auth handshake, sends one
        command, and returns its ``result`` payload.
        """
        async with websockets.connect(self._ws_url(), max_size=None) as ws:
            auth_required = json.loads(await ws.recv())
            if auth_required.get("type") != "auth_required":
                raise RuntimeError(f"Unexpected HA WS greeting: {auth_required}")

            await ws.send(json.dumps({"type": "auth", "access_token": self._config.ha_token}))
            auth_result = json.loads(await ws.recv())
            if auth_result.get("type") != "auth_ok":
                raise RuntimeError(f"HA WebSocket auth failed: {auth_result}")

            msg_id = 1
            await ws.send(json.dumps({"id": msg_id, "type": command_type, **payload}))
            while True:
                msg = json.loads(await ws.recv())
                if msg.get("id") != msg_id or msg.get("type") != "result":
                    continue  # skip unrelated events/pongs
                if not msg.get("success"):
                    raise RuntimeError(
                        f"HA WS command '{command_type}' failed: {msg.get('error')}"
                    )
                return msg.get("result")

    def scope_filter(self, entities: list[dict]) -> list[dict]:
        """Filter entities by configured scope.

        Domain filtering uses entity_id. Area and label filtering require
        the entity dicts to be enriched with 'area_id' and 'labels' fields
        (available after registry cross-referencing in discovery.py).
        Floor filtering is applied in discovery.py after area-floor mapping.
        """
        cfg = self._config
        if not any([cfg.scope_domains, cfg.scope_areas, cfg.scope_labels]):
            return entities

        result = []
        for entity in entities:
            entity_id = entity.get("entity_id", "")
            domain = entity_id.split(".")[0] if "." in entity_id else ""

            if cfg.scope_domains and domain not in cfg.scope_domains:
                continue
            if cfg.scope_areas and entity.get("area_id") not in cfg.scope_areas:
                continue
            if cfg.scope_labels:
                entity_labels = entity.get("labels") or []
                if not any(label in entity_labels for label in cfg.scope_labels):
                    continue

            result.append(entity)
        return result

    @property
    def config(self) -> Config:
        return self._config
