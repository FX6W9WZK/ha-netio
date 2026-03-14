"""Button entities for NETIO power output actions.

Per NETIO JSON API documentation, outputs support these actions:
  0 = Turn OFF        → covered by switch.py
  1 = Turn ON         → covered by switch.py
  2 = Short OFF delay → restart (button)
  3 = Short ON delay  → button
  4 = Toggle          → button
  5 = No change       → not useful

This module creates buttons for actions 2, 3, and 4.
"""

from __future__ import annotations

import logging

from homeassistant.components.button import ButtonDeviceClass, ButtonEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api import NetioApiError
from .const import ACTION_SHORT_OFF, ACTION_SHORT_ON, ACTION_TOGGLE
from .coordinator import NetioConfigEntry, NetioCoordinator
from .entity import NetioEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: NetioConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up NETIO buttons from a config entry."""
    coordinator: NetioCoordinator = entry.runtime_data

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


class NetioRestartButton(NetioEntity, ButtonEntity):
    """Button to restart (short OFF) a NETIO output.

    Per documentation: Action 2 = Short OFF delay (restart).
    Switches the output OFF for a defined time, then back ON.
    The delay is configured in the device web administration.
    During the short delay, the output is protected from other
    M2M commands.
    """

    _attr_icon = "mdi:restart"
    _attr_device_class = ButtonDeviceClass.RESTART

    def __init__(self, coordinator: NetioCoordinator, output_id: int) -> None:
        super().__init__(coordinator)
        self._output_id = output_id
        self._attr_unique_id = f"{coordinator.device_serial}_output_{output_id}_restart"

    @property
    def _output(self):
        if self.coordinator.data:
            for output in self.coordinator.data.outputs:
                if output.id == self._output_id:
                    return output
        return None

    @property
    def name(self) -> str | None:
        output = self._output
        output_name = output.name if output else f"Output {self._output_id}"
        return f"{output_name} Restart"

    async def async_press(self) -> None:
        """Execute short OFF (restart) on the output."""
        try:
            new_state = await self.coordinator.client.set_output(
                self._output_id, ACTION_SHORT_OFF
            )
            self.coordinator.async_set_updated_data(new_state)
        except NetioApiError as err:
            _LOGGER.error(
                "Failed to restart output %d: %s", self._output_id, err
            )


class NetioShortOnButton(NetioEntity, ButtonEntity):
    """Button to short ON a NETIO output.

    Per documentation: Action 3 = Short ON delay.
    Switches the output ON for a defined time, then back OFF.
    Useful for e.g. switching on a pump for a defined time.
    """

    _attr_icon = "mdi:timer-outline"

    def __init__(self, coordinator: NetioCoordinator, output_id: int) -> None:
        super().__init__(coordinator)
        self._output_id = output_id
        self._attr_unique_id = f"{coordinator.device_serial}_output_{output_id}_short_on"

    @property
    def _output(self):
        if self.coordinator.data:
            for output in self.coordinator.data.outputs:
                if output.id == self._output_id:
                    return output
        return None

    @property
    def name(self) -> str | None:
        output = self._output
        output_name = output.name if output else f"Output {self._output_id}"
        return f"{output_name} Short ON"

    async def async_press(self) -> None:
        """Execute short ON on the output."""
        try:
            new_state = await self.coordinator.client.set_output(
                self._output_id, ACTION_SHORT_ON
            )
            self.coordinator.async_set_updated_data(new_state)
        except NetioApiError as err:
            _LOGGER.error(
                "Failed to short-on output %d: %s", self._output_id, err
            )


class NetioToggleButton(NetioEntity, ButtonEntity):
    """Button to toggle a NETIO output.

    Per documentation: Action 4 = Toggle (invert the state).
    """

    _attr_icon = "mdi:toggle-switch-outline"

    def __init__(self, coordinator: NetioCoordinator, output_id: int) -> None:
        super().__init__(coordinator)
        self._output_id = output_id
        self._attr_unique_id = f"{coordinator.device_serial}_output_{output_id}_toggle"

    @property
    def _output(self):
        if self.coordinator.data:
            for output in self.coordinator.data.outputs:
                if output.id == self._output_id:
                    return output
        return None

    @property
    def name(self) -> str | None:
        output = self._output
        output_name = output.name if output else f"Output {self._output_id}"
        return f"{output_name} Toggle"

    async def async_press(self) -> None:
        """Toggle the output."""
        try:
            new_state = await self.coordinator.client.set_output(
                self._output_id, ACTION_TOGGLE
            )
            self.coordinator.async_set_updated_data(new_state)
        except NetioApiError as err:
            _LOGGER.error(
                "Failed to toggle output %d: %s", self._output_id, err
            )
