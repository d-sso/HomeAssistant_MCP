from dataclasses import dataclass, field
from dotenv import load_dotenv
import os
import sys

load_dotenv()


def _split(value: str | None) -> list[str]:
    if not value:
        return []
    return [v.strip() for v in value.split(",") if v.strip()]


@dataclass
class Config:
    ha_url: str
    ha_token: str
    scope_areas: list[str] = field(default_factory=list)
    scope_floors: list[str] = field(default_factory=list)
    scope_domains: list[str] = field(default_factory=list)
    scope_labels: list[str] = field(default_factory=list)
    mqtt_host: str = "localhost"
    mqtt_port: int = 1883
    mqtt_topic_prefix: str = "ha"
    mqtt_username: str | None = None
    mqtt_password: str | None = None
    bridge_entity_allowlist: list[str] = field(default_factory=list)


def load_config() -> Config:
    ha_url = os.getenv("HA_URL")
    ha_token = os.getenv("HA_TOKEN")

    if not ha_url or not ha_token:
        print("ERROR: HA_URL and HA_TOKEN are required", file=sys.stderr)
        sys.exit(1)

    return Config(
        ha_url=ha_url.rstrip("/"),
        ha_token=ha_token,
        scope_areas=_split(os.getenv("HA_SCOPE_AREAS")),
        scope_floors=_split(os.getenv("HA_SCOPE_FLOORS")),
        scope_domains=_split(os.getenv("HA_SCOPE_DOMAINS")),
        scope_labels=_split(os.getenv("HA_SCOPE_LABELS")),
        mqtt_host=os.getenv("MQTT_HOST", "localhost"),
        mqtt_port=int(os.getenv("MQTT_PORT", "1883")),
        mqtt_topic_prefix=os.getenv("MQTT_TOPIC_PREFIX", "ha"),
        mqtt_username=os.getenv("MQTT_USERNAME"),
        mqtt_password=os.getenv("MQTT_PASSWORD"),
        bridge_entity_allowlist=_split(os.getenv("BRIDGE_ENTITY_ALLOWLIST")),
    )
