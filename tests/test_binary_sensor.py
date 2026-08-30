"""Tests for the NETIO binary sensor platform and shared entity bases."""
from __future__ import annotations

from unittest.mock import patch

from homeassistant.const import STATE_OFF, STATE_ON, STATE_UNKNOWN
from homeassistant.helpers import entity_registry as er

from custom_components.netio_products.const import DOMAIN
from custom_components.netio_products.entity import NetioOutputEntity

from .conftest import TEST_SERIAL, make_state


def input_entity_id(hass, input_id: int) -> str | None:
    """Resolve a binary sensor entity id from its unique id."""
    ent_reg = er.async_get(hass)
    return ent_reg.async_get_entity_id(
        "binary_sensor", DOMAIN, f"{TEST_SERIAL}_input_{input_id}"
    )


async def test_input_states(hass, config_entry, setup_integration) -> None:
    """Input states map 1=closed to on and 0=open to off."""
    entity_id_1 = input_entity_id(hass, 1)
    entity_id_2 = input_entity_id(hass, 2)
    assert hass.states.get(entity_id_1).state == STATE_OFF
    assert hass.states.get(entity_id_2).state == STATE_ON
    assert "Door" in hass.states.get(entity_id_1).attributes["friendly_name"]


async def test_no_inputs_no_entities(hass, config_entry, mock_client) -> None:
    """Devices without inputs get no binary sensors."""
    mock_client.get_state.return_value = make_state(inputs=[])
    config_entry.add_to_hass(hass)
    with patch(
        "custom_components.netio_products.NetioApiClient",
        return_value=mock_client,
    ):
        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

    ent_reg = er.async_get(hass)
    binary_sensors = [
        e
        for e in er.async_entries_for_config_entry(ent_reg, config_entry.entry_id)
        if e.domain == "binary_sensor"
    ]
    assert binary_sensors == []


async def test_input_unknown_when_removed(
    hass, config_entry, setup_integration
) -> None:
    """A vanished input yields an unknown state."""
    coordinator = config_entry.runtime_data
    entity_id = input_entity_id(hass, 2)
    coordinator.async_set_updated_data(make_state(inputs=[]))
    await hass.async_block_till_done()
    assert hass.states.get(entity_id).state == STATE_UNKNOWN


async def test_output_entity_without_parent_device(
    hass, config_entry, setup_integration
) -> None:
    """NetioOutputEntity omits via_device_id without a parent id."""
    coordinator = config_entry.runtime_data
    coordinator.parent_device_id = None
    entity = NetioOutputEntity(coordinator, 42)
    info = entity._attr_device_info
    assert "via_device_id" not in info
    # Unknown output ids fall back to a generic name
    assert info["name"] == "My NETIO Output 42"
    assert info["identifiers"] == {(DOMAIN, f"{TEST_SERIAL}_output_42")}
