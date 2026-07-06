"""Config flow for NETIO integration."""

from __future__ import annotations

import logging
from typing import Any

from collections.abc import Mapping

import voluptuous as vol

from homeassistant.helpers.service_info.dhcp import DhcpServiceInfo
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_PORT, CONF_USERNAME
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import NetioApiClient, NetioApiError, NetioAuthError, NetioConnectionError
from .const import (
    CONF_ENABLE_RESTART, CONF_ENABLE_SHORT_ON, CONF_ENABLE_TOGGLE,
    DEFAULT_PASSWORD, DEFAULT_USERNAME, DOMAIN,
)

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

    session = async_get_clientsession(hass, verify_ssl=not use_ssl)
    client = NetioApiClient(
        base_url=base_url,
        username=username,
        password=password,
        session=session,
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

    VERSION = 2

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._discovered_host: str | None = None
        self._discovered_mac: str | None = None
        self._pending_data: dict[str, Any] = {}
        self._pending_title: str = "NETIO"

    @staticmethod
    def async_get_options_flow(config_entry):
        """Get the options flow handler."""
        return NetioOptionsFlow()

    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> ConfigFlowResult:
        """Handle reauthentication after an authentication failure."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ask for new credentials and validate them."""
        errors: dict[str, str] = {}
        entry = self._get_reauth_entry()

        if user_input is not None:
            username = user_input[CONF_USERNAME]
            password = user_input[CONF_PASSWORD]

            state, error = await _test_connection(
                self.hass,
                entry.data[CONF_HOST],
                entry.data[CONF_PORT],
                username,
                password,
                entry.data.get(CONF_USE_SSL, False),
            )

            if error:
                errors["base"] = error
            else:
                return self.async_update_reload_and_abort(
                    entry,
                    data_updates={
                        CONF_USERNAME: username,
                        CONF_PASSWORD: password,
                    },
                )

        return self.async_show_form(
            step_id="reauth_confirm",
            description_placeholders={"host": entry.data[CONF_HOST]},
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_USERNAME,
                        default=entry.data.get(CONF_USERNAME, DEFAULT_USERNAME),
                    ): str,
                    vol.Required(CONF_PASSWORD): str,
                }
            ),
            errors=errors,
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle reconfiguration of connection settings."""
        errors: dict[str, str] = {}
        entry = self._get_reconfigure_entry()

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
                # Make sure the user is still talking to the same device
                # before overwriting the stored connection settings.
                serial = (
                    state.agent.serial_number
                    or state.agent.mac.replace(":", "")
                    or f"{host}_{port}"
                )
                await self.async_set_unique_id(serial)
                self._abort_if_unique_id_mismatch(reason="wrong_device")

                return self.async_update_reload_and_abort(
                    entry,
                    data={
                        CONF_HOST: host,
                        CONF_PORT: port,
                        CONF_USERNAME: username,
                        CONF_PASSWORD: password,
                        CONF_USE_SSL: use_ssl,
                    },
                )

        # Pre-fill with current values
        current = entry.data
        schema = vol.Schema(
            {
                vol.Required(CONF_HOST, default=current.get(CONF_HOST, "")): str,
                vol.Optional(CONF_PORT, default=current.get(CONF_PORT, 80)): int,
                vol.Optional(
                    CONF_USERNAME,
                    default=current.get(CONF_USERNAME, DEFAULT_USERNAME),
                ): str,
                vol.Optional(
                    CONF_PASSWORD,
                    default=current.get(CONF_PASSWORD, DEFAULT_PASSWORD),
                ): str,
                vol.Optional(
                    CONF_USE_SSL,
                    default=current.get(CONF_USE_SSL, False),
                ): bool,
            }
        )

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=schema,
            errors=errors,
        )

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

        # Existing entries use the SerialNumber as unique_id, which may
        # differ from the MAC. The MAC-based check above cannot match
        # those, so also match on the stored host to avoid duplicate
        # discovery flows for already configured devices.
        for entry in self._async_current_entries(include_ignore=False):
            if entry.data.get(CONF_HOST) == discovery_info.ip:
                return self.async_abort(reason="already_configured")

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
                self._pending_data = {
                    CONF_HOST: host,
                    CONF_PORT: port,
                    CONF_USERNAME: username,
                    CONF_PASSWORD: password,
                    CONF_USE_SSL: use_ssl,
                }
                self._pending_title = title
                return await self.async_step_buttons()

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

                self._pending_data = {
                    CONF_HOST: host,
                    CONF_PORT: port,
                    CONF_USERNAME: username,
                    CONF_PASSWORD: password,
                    CONF_USE_SSL: use_ssl,
                }
                self._pending_title = title
                return await self.async_step_buttons()

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )

    async def async_step_buttons(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Second step: configure which button entities to enable."""
        if user_input is not None:
            return self.async_create_entry(
                title=self._pending_title,
                data=self._pending_data,
                options={
                    CONF_ENABLE_RESTART: user_input.get(CONF_ENABLE_RESTART, True),
                    CONF_ENABLE_SHORT_ON: user_input.get(CONF_ENABLE_SHORT_ON, True),
                    CONF_ENABLE_TOGGLE: user_input.get(CONF_ENABLE_TOGGLE, True),
                },
            )

        return self.async_show_form(
            step_id="buttons",
            data_schema=vol.Schema(
                {
                    vol.Optional(CONF_ENABLE_RESTART, default=True): bool,
                    vol.Optional(CONF_ENABLE_SHORT_ON, default=True): bool,
                    vol.Optional(CONF_ENABLE_TOGGLE, default=True): bool,
                }
            ),
        )


class NetioOptionsFlow(OptionsFlow):
    """Handle NETIO options flow.

    Allows enabling/disabling button entity types (Restart, Short ON, Toggle)
    for all outputs of the device. Disabled entities are removed from
    hass.states and won't appear in Lovelace cards.
    """

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the options."""
        if user_input is not None:
            new_options = {
                CONF_ENABLE_RESTART: user_input[CONF_ENABLE_RESTART],
                CONF_ENABLE_SHORT_ON: user_input[CONF_ENABLE_SHORT_ON],
                CONF_ENABLE_TOGGLE: user_input[CONF_ENABLE_TOGGLE],
            }

            # Show/hide button entities in the entity registry
            from homeassistant.helpers import entity_registry as er

            ent_reg = er.async_get(self.hass)
            entries = er.async_entries_for_config_entry(
                ent_reg, self.config_entry.entry_id
            )

            for entry in entries:
                if not entry.entity_id.startswith("button."):
                    continue

                should_hide = False
                if entry.entity_id.endswith("_restart"):
                    should_hide = not new_options[CONF_ENABLE_RESTART]
                elif entry.entity_id.endswith("_short_on"):
                    should_hide = not new_options[CONF_ENABLE_SHORT_ON]
                elif entry.entity_id.endswith("_toggle"):
                    should_hide = not new_options[CONF_ENABLE_TOGGLE]

                # Only toggle our own hidden_by flag; entities disabled or
                # hidden by the user/device stay untouched.
                is_hidden = entry.hidden_by is er.RegistryEntryHider.INTEGRATION

                if should_hide and entry.hidden_by is None:
                    ent_reg.async_update_entity(
                        entry.entity_id,
                        hidden_by=er.RegistryEntryHider.INTEGRATION,
                    )
                elif not should_hide and is_hidden:
                    ent_reg.async_update_entity(
                        entry.entity_id,
                        hidden_by=None,
                    )

            return self.async_create_entry(title="", data=new_options)

        # Current options with defaults
        options = self.config_entry.options
        schema = vol.Schema(
            {
                vol.Optional(
                    CONF_ENABLE_RESTART,
                    default=options.get(CONF_ENABLE_RESTART, True),
                ): bool,
                vol.Optional(
                    CONF_ENABLE_SHORT_ON,
                    default=options.get(CONF_ENABLE_SHORT_ON, True),
                ): bool,
                vol.Optional(
                    CONF_ENABLE_TOGGLE,
                    default=options.get(CONF_ENABLE_TOGGLE, True),
                ): bool,
            }
        )

        return self.async_show_form(step_id="init", data_schema=schema)
