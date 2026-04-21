# Phase 2 — Command gate (not yet implemented)
#
# This service will:
#   1. Subscribe to {MQTT_TOPIC_PREFIX}/commands/# from QA HA
#   2. Check each command against a per-domain/entity allowlist
#   3. Request human approval via HA persistent notification for non-trivial commands
#   4. On approval, forward the service call to prod HA REST API
#   5. Publish the outcome back to {MQTT_TOPIC_PREFIX}/commands/results/<token>
#
# See docs/architecture.md for the full confirmation flow diagram.
