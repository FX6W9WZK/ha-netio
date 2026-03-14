"""Switch platform for NETIO power outputs.

Each NETIO device output is represented as a switch entity.
Per JSON API documentation:
- Output state: 0=OFF, 1=ON
- Control actions: 0=off, 1=on, 2=short off, 3=short on, 4=toggle, 5=no change
"""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.switch import SwitchDeviceClass, SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api import NetioApiError
from .const import ACTION_OFF, ACTION_ON, DOMAIN, STATE_OUTPUT_ON
from .coordinator import NetioConfigEntry, NetioCoordinator
from .entity import NetioEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: NetioConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up NETIO switches from a config entry."""
    coordinator: NetioCoordinator = entry.runtime_data

    entities = [
        NetioSwitch(coordinator, output.id)
        for output in coordinator.data.outputs
    ]

    async_add_entities(entities)


class NetioSwitch(NetioEntity, SwitchEntity):
    """Representation of a NETIO power output as a switch."""

    _attr_device_class = SwitchDeviceClass.OUTLET

    def __init__(self, coordinator: NetioCoordinator, output_id: int) -> None:
        """Initialize the switch.

        Args:
            coordinator: The data update coordinator
            output_id: 1-based output ID from the NETIO device
        """
        super().__init__(coordinator)
        self._output_id = output_id
        self._attr_unique_id = f"{coordinator.device_serial}_output_{output_id}"

    @property
    def _output(self):
        """Get the current output data from the coordinator."""
        if self.coordinator.data and self.coordinator.data.outputs:
            for output in self.coordinator.data.outputs:
                if output.id == self._output_id:
                    return output
        return None

    @property
    def name(self) -> str | None:
        """Return the name of the output as configured on the device."""
        output = self._output
        if output and output.name:
            return output.name
        return f"Output {self._output_id}"

    @property
    def is_on(self) -> bool | None:
        """Return True if the output is on."""
        output = self._output
        if output is None:
            return None
        return output.state == STATE_OUTPUT_ON

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the output on.

        Per JSON API documentation, Action=1 turns the output ON.
        The POST response contains the updated device state.
        """
        try:
            new_state = await self.coordinator.client.set_output(
                self._output_id, ACTION_ON
            )
            self.coordinator.async_set_updated_data(new_state)
        except NetioApiError as err:
            _LOGGER.error("Failed to turn on output %d: %s", self._output_id, err)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the output off.

        Per JSON API documentation, Action=0 turns the output OFF.
        """
        try:
            new_state = await self.coordinator.client.set_output(
                self._output_id, ACTION_OFF
            )
            self.coordinator.async_set_updated_data(new_state)
        except NetioApiError as err:
            _LOGGER.error("Failed to turn off output %d: %s", self._output_id, err)
