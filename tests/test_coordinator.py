"""Tests for the NETIO data update coordinator."""
from __future__ import annotations

import pytest

from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.netio_products.api import (
    NetioAgent,
    NetioApiError,
    NetioAuthError,
    NetioConnectionError,
)
from custom_components.netio_products.const import DOMAIN
from custom_components.netio_products.coordinator import (
    NetioCoordinator,
    compute_serial,
)

from .conftest import TEST_SERIAL, make_output, make_state


def test_compute_serial() -> None:
    """compute_serial prefers serial, then MAC, then the fallback."""
    assert (
        compute_serial(NetioAgent(serial_number="SER", mac="aa:bb"), "fb") == "SER"
    )
    assert compute_serial(NetioAgent(mac="aa:bb:cc"), "fb") == "aabbcc"
    assert compute_serial(NetioAgent(), "fb") == "fb"


async def test_update_success(hass, config_entry, setup_integration) -> None:
    """A successful poll stores the new state."""
    coordinator: NetioCoordinator = config_entry.runtime_data
    assert coordinator.last_update_success
    assert coordinator.data.agent.serial_number == TEST_SERIAL
    assert coordinator.device_serial == TEST_SERIAL


async def test_update_auth_failed(hass, config_entry, setup_integration) -> None:
    """An auth error raises ConfigEntryAuthFailed."""
    coordinator: NetioCoordinator = config_entry.runtime_data
    setup_integration.get_state.side_effect = NetioAuthError("denied")
    with pytest.raises(ConfigEntryAuthFailed):
        await coordinator._async_update_data()


@pytest.mark.parametrize(
    "exc", [NetioConnectionError("down"), NetioApiError("broken")]
)
async def test_update_failed(hass, config_entry, setup_integration, exc) -> None:
    """Connection and API errors raise UpdateFailed."""
    coordinator: NetioCoordinator = config_entry.runtime_data
    setup_integration.get_state.side_effect = exc
    with pytest.raises(UpdateFailed):
        await coordinator._async_update_data()


async def test_device_rename(hass, config_entry, setup_integration) -> None:
    """Device and output renames propagate to the device registry."""
    coordinator: NetioCoordinator = config_entry.runtime_data
    dev_reg = dr.async_get(hass)

    setup_integration.get_state.return_value = make_state(
        device_name="Renamed",
        outputs=[
            make_output(1, "NewLamp", 1, metered=True),
            make_output(2, "Fan", 0, metered=False),
        ],
    )
    await coordinator.async_refresh()
    await hass.async_block_till_done()

    parent = dev_reg.async_get_device_by_identifier(
        (DOMAIN, TEST_SERIAL), config_entry.entry_id
    )
    assert parent.name == "Renamed"
    sub1 = dev_reg.async_get_device_by_identifier(
        (DOMAIN, f"{TEST_SERIAL}_output_1"), config_entry.entry_id
    )
    assert sub1.name == "Renamed NewLamp"


async def test_device_rename_noop(hass, config_entry, setup_integration) -> None:
    """A refresh without name changes leaves the registry alone."""
    coordinator: NetioCoordinator = config_entry.runtime_data
    dev_reg = dr.async_get(hass)
    before = dev_reg.async_get_device_by_identifier(
        (DOMAIN, TEST_SERIAL), config_entry.entry_id
    )

    await coordinator.async_refresh()
    await hass.async_block_till_done()

    after = dev_reg.async_get_device_by_identifier(
        (DOMAIN, TEST_SERIAL), config_entry.entry_id
    )
    assert after.name == before.name
    assert after.modified_at == before.modified_at


async def test_device_rename_registry_already_matches(
    hass, config_entry, setup_integration
) -> None:
    """No registry write happens when the registry already has the name."""
    coordinator: NetioCoordinator = config_entry.runtime_data
    # Force the rename code path although the registry name is current.
    coordinator._last_device_name = None
    coordinator._last_output_names = {}
    await coordinator.async_refresh()
    await hass.async_block_till_done()

    dev_reg = dr.async_get(hass)
    parent = dev_reg.async_get_device_by_identifier(
        (DOMAIN, TEST_SERIAL), config_entry.entry_id
    )
    assert parent.name == "My NETIO"
    assert coordinator._last_device_name == "My NETIO"


async def test_device_rename_unknown_device(
    hass, config_entry, setup_integration
) -> None:
    """Renames for devices not in the registry are skipped gracefully."""
    coordinator: NetioCoordinator = config_entry.runtime_data
    # Serial changes -> registry lookups miss; new output has no sub-device.
    setup_integration.get_state.return_value = make_state(
        serial="UNKNOWNSERIAL",
        device_name="Ghost",
        outputs=[make_output(99, "Extra", 1, metered=False)],
    )
    await coordinator.async_refresh()
    await hass.async_block_till_done()

    assert coordinator.last_update_success
    assert coordinator._last_device_name == "Ghost"
    assert coordinator._last_output_names == {99: "Extra"}


async def test_device_rename_empty_outputs(
    hass, config_entry, setup_integration
) -> None:
    """A state without outputs clears the tracked output names."""
    coordinator: NetioCoordinator = config_entry.runtime_data
    setup_integration.get_state.return_value = make_state(outputs=[])
    await coordinator.async_refresh()
    await hass.async_block_till_done()
    assert coordinator._last_output_names == {}


async def test_output_name_fallback(hass, config_entry, setup_integration) -> None:
    """An output without a name is tracked as 'Output <id>'."""
    coordinator: NetioCoordinator = config_entry.runtime_data
    setup_integration.get_state.return_value = make_state(
        outputs=[make_output(1, "", 1, metered=False)]
    )
    await coordinator.async_refresh()
    await hass.async_block_till_done()
    assert coordinator._last_output_names == {1: "Output 1"}


async def test_properties_without_data(hass, config_entry, mock_client) -> None:
    """Properties fall back safely before the first refresh."""
    config_entry.add_to_hass(hass)
    coordinator = NetioCoordinator(hass, mock_client, config_entry)
    assert coordinator.data is None
    assert coordinator.device_serial == config_entry.entry_id
    assert coordinator.has_metering is False
    assert coordinator.has_global_metering is False
    assert coordinator.has_inputs is False


async def test_metering_detection(hass, config_entry, setup_integration) -> None:
    """Metering flags are derived from the polled data."""
    coordinator: NetioCoordinator = config_entry.runtime_data
    assert coordinator.has_metering is True
    assert coordinator.has_global_metering is True
    assert coordinator.has_inputs is True

    coordinator.async_set_updated_data(
        make_state(
            outputs=[make_output(1, "Lamp", 1, metered=False)],
            inputs=[],
            with_global=False,
        )
    )
    assert coordinator.has_metering is False
    assert coordinator.has_global_metering is False
    assert coordinator.has_inputs is False

    coordinator.async_set_updated_data(make_state(outputs=[]))
    assert coordinator.has_metering is False
