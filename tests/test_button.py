"""Tests for the NETIO button platform."""
from __future__ import annotations

import pytest

from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er

from custom_components.netio_products.api import NetioApiError
from custom_components.netio_products.const import (
    ACTION_SHORT_OFF,
    ACTION_SHORT_ON,
    ACTION_TOGGLE,
    CONF_ENABLE_RESTART,
    CONF_ENABLE_SHORT_ON,
    CONF_ENABLE_TOGGLE,
    DOMAIN,
)

from .conftest import TEST_SERIAL


def button_entity_id(hass, output_id: int, suffix: str) -> str:
    """Resolve a button entity id from its unique id."""
    ent_reg = er.async_get(hass)
    entity_id = ent_reg.async_get_entity_id(
        "button", DOMAIN, f"{TEST_SERIAL}_output_{output_id}_{suffix}"
    )
    assert entity_id
    return entity_id


async def test_buttons_created(hass, config_entry, setup_integration) -> None:
    """All three button types exist for every output and are visible."""
    ent_reg = er.async_get(hass)
    for output_id in (1, 2):
        for suffix in ("restart", "short_on", "toggle"):
            entity_id = button_entity_id(hass, output_id, suffix)
            assert hass.states.get(entity_id) is not None
            assert ent_reg.async_get(entity_id).hidden_by is None


@pytest.mark.parametrize(
    ("suffix", "action", "match"),
    [
        ("restart", ACTION_SHORT_OFF, "Failed to restart output 1"),
        ("short_on", ACTION_SHORT_ON, "Failed to short-on output 1"),
        ("toggle", ACTION_TOGGLE, "Failed to toggle output 1"),
    ],
)
async def test_button_press_and_error(
    hass, config_entry, setup_integration, suffix, action, match
) -> None:
    """Pressing sends the correct action; API errors surface."""
    entity_id = button_entity_id(hass, 1, suffix)

    await hass.services.async_call(
        "button", "press", {ATTR_ENTITY_ID: entity_id}, blocking=True
    )
    setup_integration.set_output.assert_awaited_once_with(1, action)

    setup_integration.set_output.side_effect = NetioApiError("nope")
    with pytest.raises(HomeAssistantError, match=match):
        await hass.services.async_call(
            "button", "press", {ATTR_ENTITY_ID: entity_id}, blocking=True
        )


async def test_buttons_hidden_by_options(hass, config_entry, mock_client) -> None:
    """Disabled button options hide the entities by default."""
    from unittest.mock import patch

    config_entry.add_to_hass(hass)
    hass.config_entries.async_update_entry(
        config_entry,
        options={
            CONF_ENABLE_RESTART: False,
            CONF_ENABLE_SHORT_ON: False,
            CONF_ENABLE_TOGGLE: False,
        },
    )
    with patch(
        "custom_components.netio_products.NetioApiClient",
        return_value=mock_client,
    ):
        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

    ent_reg = er.async_get(hass)
    for suffix in ("restart", "short_on", "toggle"):
        entity_id = button_entity_id(hass, 1, suffix)
        assert (
            ent_reg.async_get(entity_id).hidden_by
            is er.RegistryEntryHider.INTEGRATION
        )
