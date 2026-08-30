"""Tests for the NETIO config, options, reauth and reconfigure flows."""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from homeassistant.config_entries import SOURCE_DHCP, SOURCE_USER
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_PORT, CONF_USERNAME
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.service_info.dhcp import DhcpServiceInfo

from custom_components.netio_products.api import (
    NetioApiError,
    NetioAuthError,
    NetioConnectionError,
)
from custom_components.netio_products.const import (
    CONF_ENABLE_RESTART,
    CONF_ENABLE_SHORT_ON,
    CONF_ENABLE_TOGGLE,
    DOMAIN,
)

from pytest_homeassistant_custom_component.common import MockConfigEntry

from .conftest import TEST_SERIAL, make_state

USER_INPUT = {
    CONF_HOST: "1.2.3.4",
    CONF_PORT: 80,
    CONF_USERNAME: "netio",
    CONF_PASSWORD: "netio",
    "use_ssl": False,
}

BUTTON_INPUT = {
    CONF_ENABLE_RESTART: True,
    CONF_ENABLE_SHORT_ON: True,
    CONF_ENABLE_TOGGLE: False,
}

GET_STATE = "custom_components.netio_products.api.NetioApiClient.get_state"


async def test_user_flow_success(hass, mock_setup_entry) -> None:
    """Full user flow: connection test, buttons step, entry creation."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {}

    with patch(GET_STATE, AsyncMock(return_value=make_state())):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], USER_INPUT
        )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "buttons"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], BUTTON_INPUT
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "My NETIO"
    assert result["data"] == USER_INPUT
    assert result["options"] == BUTTON_INPUT
    assert result["result"].unique_id == TEST_SERIAL
    assert len(mock_setup_entry.mock_calls) == 1


@pytest.mark.parametrize(
    ("exc", "error"),
    [
        (NetioAuthError("bad"), "invalid_auth"),
        (NetioConnectionError("down"), "cannot_connect"),
        (NetioApiError("api"), "cannot_connect"),
        (RuntimeError("boom"), "unknown"),
    ],
)
async def test_user_flow_errors_and_recovery(
    hass, mock_setup_entry, exc, error
) -> None:
    """Connection errors are shown and the flow can recover."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    with patch(GET_STATE, AsyncMock(side_effect=exc)):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], USER_INPUT
        )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {"base": error}

    with patch(GET_STATE, AsyncMock(return_value=make_state())):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], USER_INPUT
        )
    assert result["step_id"] == "buttons"

    result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    # Buttons step defaults everything to enabled
    assert result["options"] == {
        CONF_ENABLE_RESTART: True,
        CONF_ENABLE_SHORT_ON: True,
        CONF_ENABLE_TOGGLE: True,
    }


async def test_user_flow_duplicate_aborts(hass, config_entry) -> None:
    """Configuring an already known device aborts."""
    config_entry.add_to_hass(hass)
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    with patch(GET_STATE, AsyncMock(return_value=make_state())):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], USER_INPUT
        )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_user_flow_serial_fallback_mac(hass, mock_setup_entry) -> None:
    """Without a serial number, the MAC becomes the unique id."""
    state = make_state(serial="", device_name="", model="PowerCable")
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    with patch(GET_STATE, AsyncMock(return_value=state)):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], USER_INPUT
        )
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    assert result["result"].unique_id == "24A42C123456"
    assert result["title"] == "PowerCable"


async def test_user_flow_serial_fallback_host(hass, mock_setup_entry) -> None:
    """Without serial and MAC, host_port becomes the unique id."""
    state = make_state(serial="", mac="", device_name="", model="")
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    with patch(GET_STATE, AsyncMock(return_value=state)):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], USER_INPUT
        )
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    assert result["result"].unique_id == "1.2.3.4_80"
    assert result["title"] == "NETIO 1.2.3.4"


DHCP_INFO = DhcpServiceInfo(
    ip="1.2.3.4", hostname="netio-device", macaddress="24a42c123456"
)


async def test_dhcp_flow_success(hass, mock_setup_entry) -> None:
    """DHCP discovery leads to confirm, buttons and entry creation."""
    with patch(GET_STATE, AsyncMock(return_value=make_state())):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_DHCP}, data=DHCP_INFO
        )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "dhcp_confirm"

    flow = hass.config_entries.flow.async_get(result["flow_id"])
    assert flow["context"]["title_placeholders"] == {
        "name": "My NETIO",
        "host": "1.2.3.4",
    }

    with patch(GET_STATE, AsyncMock(return_value=make_state())):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_PORT: 80, CONF_USERNAME: "netio", CONF_PASSWORD: "netio"},
        )
    assert result["step_id"] == "buttons"

    result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "My NETIO"
    assert result["data"][CONF_HOST] == "1.2.3.4"
    assert result["result"].unique_id == TEST_SERIAL


async def test_dhcp_flow_unreachable_device_name(hass) -> None:
    """If the device is unreachable, the placeholder name is generic."""
    with patch(GET_STATE, AsyncMock(side_effect=NetioConnectionError("down"))):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_DHCP}, data=DHCP_INFO
        )
    assert result["step_id"] == "dhcp_confirm"
    flow = hass.config_entries.flow.async_get(result["flow_id"])
    assert flow["context"]["title_placeholders"]["name"] == "NETIO"


async def test_dhcp_flow_confirm_error_and_fallback_serial(hass, mock_setup_entry) -> None:
    """Confirm step shows errors; empty agent falls back to the MAC."""
    with patch(GET_STATE, AsyncMock(side_effect=NetioConnectionError("down"))):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_DHCP}, data=DHCP_INFO
        )

    with patch(GET_STATE, AsyncMock(side_effect=NetioAuthError("bad"))):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_USERNAME: "netio", CONF_PASSWORD: "wrong"},
        )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "dhcp_confirm"
    assert result["errors"] == {"base": "invalid_auth"}

    state = make_state(serial="", mac="", device_name="", model="")
    with patch(GET_STATE, AsyncMock(return_value=state)):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_USERNAME: "netio", CONF_PASSWORD: "netio"},
        )
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["result"].unique_id == "24A42C123456"
    assert result["title"] == "NETIO 1.2.3.4"


async def test_dhcp_flow_already_configured_mac(hass) -> None:
    """DHCP discovery aborts for a known MAC and updates the host."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="24A42C123456",
        version=2,
        data={
            CONF_HOST: "9.9.9.9",
            CONF_PORT: 80,
            CONF_USERNAME: "netio",
            CONF_PASSWORD: "netio",
            "use_ssl": False,
        },
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_DHCP}, data=DHCP_INFO
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
    assert entry.data[CONF_HOST] == "1.2.3.4"


async def test_dhcp_flow_already_configured_host(hass) -> None:
    """DHCP discovery aborts when the host matches an existing entry."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="OTHERSERIAL",
        version=2,
        data={
            CONF_HOST: "1.2.3.4",
            CONF_PORT: 80,
            CONF_USERNAME: "netio",
            CONF_PASSWORD: "netio",
            "use_ssl": False,
        },
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_DHCP}, data=DHCP_INFO
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_dhcp_confirm_duplicate_serial_aborts(hass) -> None:
    """The confirm step aborts if the serial is already configured."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=TEST_SERIAL,
        version=2,
        data={
            CONF_HOST: "9.9.9.9",
            CONF_PORT: 80,
            CONF_USERNAME: "netio",
            CONF_PASSWORD: "netio",
            "use_ssl": False,
        },
    )
    entry.add_to_hass(hass)

    other_info = DhcpServiceInfo(
        ip="1.2.3.4", hostname="netio-device", macaddress="24a42cffffff"
    )
    with patch(GET_STATE, AsyncMock(side_effect=NetioConnectionError("down"))):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_DHCP}, data=other_info
        )
    assert result["step_id"] == "dhcp_confirm"

    with patch(GET_STATE, AsyncMock(return_value=make_state())):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_USERNAME: "netio", CONF_PASSWORD: "netio"},
        )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_reconfigure_flow_success(
    hass, config_entry, mock_setup_entry
) -> None:
    """Reconfiguring updates the stored connection settings."""
    config_entry.add_to_hass(hass)
    result = await config_entry.start_reconfigure_flow(hass)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reconfigure"

    new_input = {
        CONF_HOST: "10.0.0.5",
        CONF_PORT: 8080,
        CONF_USERNAME: "admin",
        CONF_PASSWORD: "secret",
        "use_ssl": True,
    }
    with patch(GET_STATE, AsyncMock(return_value=make_state())):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], new_input
        )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    assert config_entry.data == new_input
    await hass.async_block_till_done()


async def test_reconfigure_flow_wrong_device(hass, config_entry) -> None:
    """Reconfiguring aborts when a different device answers."""
    config_entry.add_to_hass(hass)
    result = await config_entry.start_reconfigure_flow(hass)

    with patch(
        GET_STATE, AsyncMock(return_value=make_state(serial="DIFFERENT"))
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_HOST: "10.0.0.5",
                CONF_PORT: 80,
                CONF_USERNAME: "netio",
                CONF_PASSWORD: "netio",
                "use_ssl": False,
            },
        )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "wrong_device"


async def test_reconfigure_flow_error(hass, config_entry) -> None:
    """Reconfigure shows connection errors in the form."""
    config_entry.add_to_hass(hass)
    result = await config_entry.start_reconfigure_flow(hass)

    with patch(GET_STATE, AsyncMock(side_effect=NetioConnectionError("down"))):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_HOST: "10.0.0.5",
                CONF_PORT: 80,
                CONF_USERNAME: "netio",
                CONF_PASSWORD: "netio",
                "use_ssl": False,
            },
        )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reconfigure"
    assert result["errors"] == {"base": "cannot_connect"}


async def test_reauth_flow_success(
    hass, config_entry, mock_setup_entry
) -> None:
    """Reauth stores new working credentials."""
    config_entry.add_to_hass(hass)
    result = await config_entry.start_reauth_flow(hass)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reauth_confirm"

    with patch(GET_STATE, AsyncMock(return_value=make_state())):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_USERNAME: "netio", CONF_PASSWORD: "newpass"},
        )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert config_entry.data[CONF_PASSWORD] == "newpass"
    await hass.async_block_till_done()


async def test_reauth_flow_error(hass, config_entry) -> None:
    """Reauth shows an error for still-invalid credentials."""
    config_entry.add_to_hass(hass)
    result = await config_entry.start_reauth_flow(hass)

    with patch(GET_STATE, AsyncMock(side_effect=NetioAuthError("bad"))):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_USERNAME: "netio", CONF_PASSWORD: "stillwrong"},
        )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reauth_confirm"
    assert result["errors"] == {"base": "invalid_auth"}


async def test_options_flow_hide_and_unhide(hass, config_entry, setup_integration) -> None:
    """The options flow hides and unhides button entities."""
    ent_reg = er.async_get(hass)

    def button(uid_suffix: str):
        entity_id = ent_reg.async_get_entity_id(
            "button", DOMAIN, f"{TEST_SERIAL}_output_1_{uid_suffix}"
        )
        return ent_reg.async_get(entity_id)

    switch_id = ent_reg.async_get_entity_id(
        "switch", DOMAIN, f"{TEST_SERIAL}_output_1"
    )

    assert button("restart").hidden_by is None
    assert button("toggle").hidden_by is None

    # A user-disabled button keeps its disabled_by through the options flow
    ent_reg.async_update_entity(
        button("short_on").entity_id,
        disabled_by=er.RegistryEntryDisabler.USER,
    )
    # A user-hidden button must never be unhidden by the integration
    restart2_id = ent_reg.async_get_entity_id(
        "button", DOMAIN, f"{TEST_SERIAL}_output_2_restart"
    )
    ent_reg.async_update_entity(
        restart2_id, hidden_by=er.RegistryEntryHider.USER
    )

    result = await hass.config_entries.options.async_init(config_entry.entry_id)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "init"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            CONF_ENABLE_RESTART: False,
            CONF_ENABLE_SHORT_ON: False,
            CONF_ENABLE_TOGGLE: False,
        },
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()

    assert button("restart").hidden_by is er.RegistryEntryHider.INTEGRATION
    assert button("toggle").hidden_by is er.RegistryEntryHider.INTEGRATION
    short_on = button("short_on")
    assert short_on.hidden_by is er.RegistryEntryHider.INTEGRATION
    assert short_on.disabled_by is er.RegistryEntryDisabler.USER
    # Non-button entities are untouched
    assert ent_reg.async_get(switch_id).hidden_by is None

    # Unhide everything again
    result = await hass.config_entries.options.async_init(config_entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            CONF_ENABLE_RESTART: True,
            CONF_ENABLE_SHORT_ON: True,
            CONF_ENABLE_TOGGLE: True,
        },
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()

    assert button("restart").hidden_by is None
    assert button("toggle").hidden_by is None
    assert button("short_on").hidden_by is None
    # User-hidden entities stay hidden
    assert ent_reg.async_get(restart2_id).hidden_by is er.RegistryEntryHider.USER
