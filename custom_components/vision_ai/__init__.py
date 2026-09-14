"""Vision AI Detection Database — Home Assistant custom integration.

Provides a local SQLite database for storing AI camera detection events
with full metadata (timestamps, counts, analysis text, snapshot paths).

Services:
  - vision_ai.record_detection: Insert a detection record
  - vision_ai.query_detections: Query recent detections (returns response)
  - vision_ai.get_stats: Get summary statistics (returns response)
"""

from __future__ import annotations

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall, ServiceResponse, SupportsResponse
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import ConfigType

from .const import CONF_BIRD_BUDDY_ENABLED, DOMAIN, LOGGER
from .db import VisionAIDatabase

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

RECORD_SCHEMA = vol.Schema(
    {
        vol.Required("timestamp"): cv.string,
        vol.Required("camera"): cv.string,
        vol.Required("area"): cv.string,
        vol.Required("det_type"): cv.string,
        vol.Optional("people_count", default=0): vol.Coerce(int),
        vol.Optional("vehicle_count", default=0): vol.Coerce(int),
        vol.Optional("animal_count", default=0): vol.Coerce(int),
        vol.Optional("detected_objects", default=""): vol.Any(cv.string, None),
        vol.Optional("analysis_text", default=""): cv.string,
        vol.Optional("snapshot_path", default=""): cv.string,
    }
)

QUERY_SCHEMA = vol.Schema(
    {
        vol.Optional("camera"): cv.string,
        vol.Optional("det_type"): cv.string,
        vol.Optional("hours", default=24): vol.Coerce(int),
        vol.Optional("limit", default=100): vol.Coerce(int),
    }
)

STATS_SCHEMA = vol.Schema(
    {
        vol.Optional("hours", default=24): vol.Coerce(int),
    }
)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Vision AI integration."""
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Vision AI from a config entry."""
    db = VisionAIDatabase(hass)
    await db.async_setup()
    hass.data[DOMAIN]["db"] = db

    # Store Bird Buddy toggle state so automations can read it
    bird_buddy_enabled = entry.options.get(CONF_BIRD_BUDDY_ENABLED, False)
    hass.data[DOMAIN]["bird_buddy_enabled"] = bird_buddy_enabled
    LOGGER.info("Vision AI: bird_buddy_enabled=%s", bird_buddy_enabled)

    # Listen for options updates
    entry.async_on_unload(entry.add_update_listener(_async_options_updated))

    # --- Service: record_detection ---
    async def handle_record_detection(call: ServiceCall) -> None:
        """Handle the record_detection service call."""
        row_id = await db.async_record_detection(dict(call.data))
        LOGGER.debug("Recorded detection id=%s", row_id)

    # --- Service: query_detections (returns response) ---
    async def handle_query_detections(call: ServiceCall) -> ServiceResponse:
        """Handle the query_detections service call."""
        results = await db.async_query_detections(
            camera=call.data.get("camera"),
            det_type=call.data.get("det_type"),
            hours=call.data.get("hours", 24),
            limit=call.data.get("limit", 100),
        )
        return {"detections": results, "count": len(results)}

    # --- Service: get_stats (returns response) ---
    async def handle_get_stats(call: ServiceCall) -> ServiceResponse:
        """Handle the get_stats service call."""
        stats = await db.async_get_stats(hours=call.data.get("hours", 24))
        return stats

    hass.services.async_register(
        DOMAIN, "record_detection", handle_record_detection, schema=RECORD_SCHEMA
    )
    hass.services.async_register(
        DOMAIN,
        "query_detections",
        handle_query_detections,
        schema=QUERY_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )
    hass.services.async_register(
        DOMAIN,
        "get_stats",
        handle_get_stats,
        schema=STATS_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )

    LOGGER.info("Vision AI Detection Database services registered")
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    hass.services.async_remove(DOMAIN, "record_detection")
    hass.services.async_remove(DOMAIN, "query_detections")
    hass.services.async_remove(DOMAIN, "get_stats")
    hass.data[DOMAIN].pop("db", None)
    hass.data[DOMAIN].pop("bird_buddy_enabled", None)
    return True


async def _async_options_updated(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update — refresh Bird Buddy toggle."""
    bird_buddy_enabled = entry.options.get(CONF_BIRD_BUDDY_ENABLED, False)
    hass.data.setdefault(DOMAIN, {})["bird_buddy_enabled"] = bird_buddy_enabled
    LOGGER.info("Vision AI: bird_buddy_enabled updated to %s", bird_buddy_enabled)
