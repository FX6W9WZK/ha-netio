"""Config flow for NETIO integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.helpers.service_info.dhcp import DhcpServiceInfo
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


async def _test_connection(
    hass, host: str, port: int, username: str, password: str, use_ssl: bool
):
    """Test connection to a NETIO device. Returns (state, error_key)."""
    scheme = "https" if use_ssl else "http"
    base_url = f"{scheme}://{host}:{port}"

    session = async_get_clientsession(hass, verify_ssl=False)
    client = NetioApiClient(
        base_url=base_url,
        username=username,
        password=password,
        session=session,
        verify_ssl=not use_ssl,
    )

    try:
        state = await client.get_state()
        return state, None
    except NetioAuthError:
        return None, "invalid_auth"
    except NetioConnectionError as err:
        _LOGGER.debug("Connection error to %s: %s", base_url, err)
        return None, "cannot_connect"
    except NetioApiError as err:
        _LOGGER.debug("API error from %s: %s", base_url, err)
        return None, "cannot_connect"
    except Exception as err:
        _LOGGER.exception("Unexpected error connecting to %s: %s", base_url, err)
        return None, "unknown"


class NetioConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for NETIO devices."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._discovered_host: str | None = None
        self._discovered_mac: str | None = None

    async def async_step_dhcp(
        self, discovery_info: DhcpServiceInfo
    ) -> ConfigFlowResult:
        """Handle DHCP discovery.

        NETIO devices use MAC prefix 24:A4:2C. When HA sees a device
        with this prefix via DHCP, it triggers this flow.
        """
        self._discovered_host = discovery_info.ip
        self._discovered_mac = discovery_info.macaddress

        mac_clean = discovery_info.macaddress.replace(":", "").upper()
        await self.async_set_unique_id(mac_clean)
        self._abort_if_unique_id_configured(updates={CONF_HOST: discovery_info.ip})

        # Try to connect with default credentials to get device info
        state, _ = await _test_connection(
            self.hass, discovery_info.ip, 80,
            DEFAULT_USERNAME, DEFAULT_PASSWORD, False,
        )
        name = "NETIO"
        if state:
            name = state.agent.device_name or state.agent.model or "NETIO"

        self.context["title_placeholders"] = {
            "name": name,
            "host": discovery_info.ip,
        }

        return await self.async_step_dhcp_confirm()

    async def async_step_dhcp_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Confirm DHCP-discovered device and collect credentials."""
        errors: dict[str, str] = {}

        if user_input is not None:
            host = self._discovered_host
            port = user_input.get(CONF_PORT, 80)
            username = user_input[CONF_USERNAME]
            password = user_input[CONF_PASSWORD]
            use_ssl = user_input.get(CONF_USE_SSL, False)

            state, error = await _test_connection(
                self.hass, host, port, username, password, use_ssl,
            )

            if error:
                errors["base"] = error
            else:
                serial = (
                    state.agent.serial_number
                    or state.agent.mac.replace(":", "")
                    or self._discovered_mac.replace(":", "").upper()
                )
                await self.async_set_unique_id(serial)
                self._abort_if_unique_id_configured()

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
            step_id="dhcp_confirm",
            description_placeholders={
                "host": self._discovered_host,
            },
            data_schema=vol.Schema(
                {
                    vol.Optional(CONF_PORT, default=80): int,
                    vol.Optional(CONF_USERNAME, default=DEFAULT_USERNAME): str,
                    vol.Optional(CONF_PASSWORD, default=DEFAULT_PASSWORD): str,
                    vol.Optional(CONF_USE_SSL, default=False): bool,
                }
            ),
            errors=errors,
        )

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

            state, error = await _test_connection(
                self.hass, host, port, username, password, use_ssl,
            )

            if error:
                errors["base"] = error
            else:
                serial = (
                    state.agent.serial_number
                    or state.agent.mac.replace(":", "")
                    or f"{host}_{port}"
                )
                await self.async_set_unique_id(serial)
                self._abort_if_unique_id_configured()

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
