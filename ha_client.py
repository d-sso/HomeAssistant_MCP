import httpx
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
