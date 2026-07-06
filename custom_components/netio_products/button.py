"""Button entities for NETIO power output actions.

Per NETIO JSON API documentation, outputs support these actions:
  0 = Turn OFF        → covered by switch.py
  1 = Turn ON         → covered by switch.py
  2 = Short OFF delay → restart (button)
  3 = Short ON delay  → button
  4 = Toggle          → button
  5 = No change       → not useful

This module creates buttons for actions 2, 3, and 4.
Each button is registered under the outlet's sub-device.
"""

from __future__ import annotations

import logging

from homeassistant.components.button import ButtonDeviceClass, ButtonEntity
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api import NetioApiError
from .const import ACTION_SHORT_OFF, ACTION_SHORT_ON, ACTION_TOGGLE, CONF_ENABLE_RESTART, CONF_ENABLE_SHORT_ON, CONF_ENABLE_TOGGLE
from .coordinator import NetioConfigEntry, NetioCoordinator
from .entity import NetioOutputEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: NetioConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up NETIO buttons from a config entry."""
    coordinator = entry.runtime_data

    entities: list[ButtonEntity] = []
    for output in coordinator.data.outputs:
        entities.append(
            NetioRestartButton(coordinator, output.id)
        )
        entities.append(
            NetioShortOnButton(coordinator, output.id)
        )
        entities.append(
            NetioToggleButton(coordinator, output.id)
        )

    async_add_entities(entities)


class NetioRestartButton(NetioOutputEntity, ButtonEntity):
    """Button to restart (short OFF) a NETIO output.

    Per documentation: Action 2 = Short OFF delay (restart).
    Switches the output OFF for a defined time, then back ON.
    The delay is configured in the device web administration.
    During the short delay, the output is protected from other
    M2M commands.
    """

    _attr_icon = "mdi:restart"
    _attr_device_class = ButtonDeviceClass.RESTART
    _attr_entity_category = EntityCategory.CONFIG
    _attr_translation_key = "restart"

    def __init__(self, coordinator: NetioCoordinator, output_id: int) -> None:
        super().__init__(coordinator, output_id)
        self._attr_unique_id = f"{coordinator.device_serial}_output_{output_id}_restart"
        self._attr_entity_registry_visible_default = (
            coordinator.config_entry.options.get(CONF_ENABLE_RESTART, True)
        )

    async def async_press(self) -> None:
        """Execute short OFF (restart) on the output."""
        try:
            new_state = await self.coordinator.client.set_output(
                self._output_id, ACTION_SHORT_OFF
            )
            self.coordinator.async_set_updated_data(new_state)
        except NetioApiError as err:
            raise HomeAssistantError(
                f"Failed to restart output {self._output_id}: {err}"
            ) from err


class NetioShortOnButton(NetioOutputEntity, ButtonEntity):
    """Button to short ON a NETIO output.

    Per documentation: Action 3 = Short ON delay.
    Switches the output ON for a defined time, then back OFF.
    Useful for e.g. switching on a pump for a defined time.
    """

    _attr_icon = "mdi:timer-outline"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_translation_key = "short_on"

    def __init__(self, coordinator: NetioCoordinator, output_id: int) -> None:
        super().__init__(coordinator, output_id)
        self._attr_unique_id = f"{coordinator.device_serial}_output_{output_id}_short_on"
        self._attr_entity_registry_visible_default = (
            coordinator.config_entry.options.get(CONF_ENABLE_SHORT_ON, True)
        )

    async def async_press(self) -> None:
        """Execute short ON on the output."""
        try:
            new_state = await self.coordinator.client.set_output(
                self._output_id, ACTION_SHORT_ON
            )
            self.coordinator.async_set_updated_data(new_state)
        except NetioApiError as err:
            raise HomeAssistantError(
                f"Failed to short-on output {self._output_id}: {err}"
            ) from err


class NetioToggleButton(NetioOutputEntity, ButtonEntity):
    """Button to toggle a NETIO output.

    Per documentation: Action 4 = Toggle (invert the state).
    """

    _attr_icon = "mdi:toggle-switch-outline"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_translation_key = "toggle"

    def __init__(self, coordinator: NetioCoordinator, output_id: int) -> None:
        super().__init__(coordinator, output_id)
        self._attr_unique_id = f"{coordinator.device_serial}_output_{output_id}_toggle"
        self._attr_entity_registry_visible_default = (
            coordinator.config_entry.options.get(CONF_ENABLE_TOGGLE, True)
        )

    async def async_press(self) -> None:
        """Toggle the output."""
        try:
            new_state = await self.coordinator.client.set_output(
                self._output_id, ACTION_TOGGLE
            )
            self.coordinator.async_set_updated_data(new_state)
        except NetioApiError as err:
            raise HomeAssistantError(
                f"Failed to toggle output {self._output_id}: {err}"
            ) from err
