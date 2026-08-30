"""Binary sensor platform for NETIO digital inputs.

Per JSON API documentation, some devices (e.g. PowerDIN 4PZ) have
digital inputs with:
- State: 0 = "open" / ON, 1 = "closed" / OFF
- S0Counter: pulse counter (handled in sensor.py)
"""

from __future__ import annotations

import logging

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import NetioConfigEntry, NetioCoordinator
from .entity import NetioEntity

_LOGGER = logging.getLogger(__name__)

# Writes go through async_set_updated_data; reads come from the coordinator.
PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: NetioConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up NETIO binary sensors from a config entry."""
    coordinator = entry.runtime_data

    if not coordinator.has_inputs:
        return

    entities = [
        NetioInputBinarySensor(coordinator, inp.id)
        for inp in coordinator.data.inputs
    ]

    async_add_entities(entities)


class NetioInputBinarySensor(NetioEntity, BinarySensorEntity):
    """Binary sensor for a NETIO digital input.

    Per NETIO documentation:
    - State 0 = "open" / ON
    - State 1 = "closed" / OFF
    """

    _attr_translation_key = "input"

    def __init__(
        self, coordinator: NetioCoordinator, input_id: int
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator)
        self._input_id = input_id
        self._attr_unique_id = (
            f"{coordinator.device_serial}_input_{input_id}"
        )
        input_name = f"Input {input_id}"
        for inp in coordinator.data.inputs:
            if inp.id == input_id and inp.name:
                input_name = inp.name
                break
        self._attr_translation_placeholders = {"input_name": input_name}

    @property
    def _input(self):
        """Get the current input data."""
        if self.coordinator.data:
            for inp in self.coordinator.data.inputs:
                if inp.id == self._input_id:
                    return inp
        return None

    @property
    def is_on(self) -> bool | None:
        """Return True if the input is in 'closed' state.

        NETIO documentation: State 0 = open, State 1 = closed.
        We map closed (1) to is_on=True (contact made).
        """
        inp = self._input
        if inp is None:
            return None
        return inp.state == 1
