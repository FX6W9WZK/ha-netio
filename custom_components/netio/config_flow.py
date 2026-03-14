"""Config flow for NETIO integration."""

from __future__ import annotations

import logging
from typing import Any

import aiohttp
import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_PORT, CONF_USERNAME
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import NetioApiClient, NetioApiError, NetioAuthError, NetioConnectionError
from .const import DEFAULT_PASSWORD, DEFAULT_USERNAME, DOMAIN

_LOGGER = logging.getLogger(__name__)

CONF_USE_SSL = "use_ssl"

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Optional(CONF_PORT, default=80): int,
        vol.Optional(CONF_USERNAME, default=DEFAULT_USERNAME): str,
        vol.Optional(CONF_PASSWORD, default=DEFAULT_PASSWORD): str,
        vol.Optional(CONF_USE_SSL, default=False): bool,
    }
)


class NetioConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for NETIO devices."""

    VERSION = 1

    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            host = user_input[CONF_HOST]
            port = user_input[CONF_PORT]
            username = user_input[CONF_USERNAME]
            password = user_input[CONF_PASSWORD]
            use_ssl = user_input[CONF_USE_SSL]

            scheme = "https" if use_ssl else "http"
            base_url = f"{scheme}://{host}:{port}"

            # Test connection to the device
            session = async_get_clientsession(self.hass, verify_ssl=False)
            client = NetioApiClient(
                base_url=base_url,
                username=username,
                password=password,
                session=session,
                verify_ssl=not use_ssl,  # self-signed certs are common on NETIO
            )

            try:
                state = await client.get_state()
            except NetioAuthError:
                errors["base"] = "invalid_auth"
            except NetioConnectionError:
                errors["base"] = "cannot_connect"
            except NetioApiError:
                errors["base"] = "cannot_connect"
            else:
                # Use serial number as unique ID per JSON API docs
                serial = (
                    state.agent.serial_number
                    or state.agent.mac.replace(":", "")
                    or f"{host}_{port}"
                )
                await self.async_set_unique_id(serial)
                self._abort_already_configured()

                title = (
                    state.agent.device_name
                    or state.agent.model
                    or f"NETIO {host}"
                )

                return self.async_create_entry(
                    title=title,
                    data={
                        CONF_HOST: host,
                        CONF_PORT: port,
                        CONF_USERNAME: username,
                        CONF_PASSWORD: password,
                        CONF_USE_SSL: use_ssl,
                    },
                )

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )
