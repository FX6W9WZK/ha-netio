"""Tests for the NETIO switch platform."""
from __future__ import annotations

import pytest

from homeassistant.const import (
    ATTR_ENTITY_ID,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    STATE_OFF,
    STATE_ON,
    STATE_UNKNOWN,
)
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er

from custom_components.netio_products.api import NetioApiError
from custom_components.netio_products.const import (
    ACTION_OFF,
    ACTION_ON,
    DOMAIN,
)

from .conftest import TEST_SERIAL, make_output, make_state


def switch_entity_id(hass, output_id: int) -> str:
    """Resolve a switch entity id from its unique id."""
    ent_reg = er.async_get(hass)
    entity_id = ent_reg.async_get_entity_id(
        "switch", DOMAIN, f"{TEST_SERIAL}_output_{output_id}"
    )
    assert entity_id
    return entity_id


async def test_switch_states(hass, config_entry, setup_integration) -> None:
    """Switch states reflect the polled output states."""
    assert hass.states.get(switch_entity_id(hass, 1)).state == STATE_ON
    assert hass.states.get(switch_entity_id(hass, 2)).state == STATE_OFF


async def test_switch_turn_on(hass, config_entry, setup_integration) -> None:
    """Turning on posts Action=1 and applies the returned state."""
    setup_integration.set_output.return_value = make_state(
        outputs=[
            make_output(1, "Lamp", 1, metered=True),
            make_output(2, "Fan", 1, metered=False),
        ]
    )
    await hass.services.async_call(
        "switch",
        SERVICE_TURN_ON,
        {ATTR_ENTITY_ID: switch_entity_id(hass, 2)},
        blocking=True,
    )
    setup_integration.set_output.assert_awaited_once_with(2, ACTION_ON)
    assert hass.states.get(switch_entity_id(hass, 2)).state == STATE_ON


async def test_switch_turn_off(hass, config_entry, setup_integration) -> None:
    """Turning off posts Action=0 and applies the returned state."""
    setup_integration.set_output.return_value = make_state(
        outputs=[
            make_output(1, "Lamp", 0, metered=True),
            make_output(2, "Fan", 0, metered=False),
        ]
    )
    await hass.services.async_call(
        "switch",
        SERVICE_TURN_OFF,
        {ATTR_ENTITY_ID: switch_entity_id(hass, 1)},
        blocking=True,
    )
    setup_integration.set_output.assert_awaited_once_with(1, ACTION_OFF)
    assert hass.states.get(switch_entity_id(hass, 1)).state == STATE_OFF


@pytest.mark.parametrize(
    ("service", "match"),
    [
        (SERVICE_TURN_ON, "Failed to turn on output 1"),
        (SERVICE_TURN_OFF, "Failed to turn off output 1"),
    ],
)
async def test_switch_error(
    hass, config_entry, setup_integration, service, match
) -> None:
    """API errors surface as HomeAssistantError."""
    setup_integration.set_output.side_effect = NetioApiError("nope")
    with pytest.raises(HomeAssistantError, match=match):
        await hass.services.async_call(
            "switch",
            service,
            {ATTR_ENTITY_ID: switch_entity_id(hass, 1)},
            blocking=True,
        )
    # State is unchanged
    assert hass.states.get(switch_entity_id(hass, 1)).state == STATE_ON


async def test_switch_unknown_when_output_missing(
    hass, config_entry, setup_integration
) -> None:
    """The switch reports unknown when its output disappears."""
    coordinator = config_entry.runtime_data
    entity_id = switch_entity_id(hass, 2)
    coordinator.async_set_updated_data(
        make_state(outputs=[make_output(1, "Lamp", 1, metered=True)])
    )
    await hass.async_block_till_done()
    assert hass.states.get(entity_id).state == STATE_UNKNOWN
