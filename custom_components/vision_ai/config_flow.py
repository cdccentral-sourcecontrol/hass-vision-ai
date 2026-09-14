"""Config flow for Vision AI Detection Database."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.core import callback

from .const import CONF_BIRD_BUDDY_ENABLED, DOMAIN


class VisionAIConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Vision AI."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Return the options flow handler."""
        return VisionAIOptionsFlow()

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step — no configuration needed."""
        # Only allow a single instance
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()

        if user_input is not None:
            return self.async_create_entry(
                title="Vision AI Detection Database",
                data={},
            )

        return self.async_show_form(step_id="user")


class VisionAIOptionsFlow(OptionsFlow):
    """Handle Vision AI options."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(data=user_input)

        current = self.config_entry.options
        schema = vol.Schema(
            {
                vol.Optional(
                    CONF_BIRD_BUDDY_ENABLED,
                    default=current.get(CONF_BIRD_BUDDY_ENABLED, False),
                ): bool,
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
