"""Sensor platform for NETIO energy metering.

Creates sensor entities for electrical measurements.
Per JSON API documentation, metering is available on:
  PowerPDU 4C, PowerCable REST 101x, PowerBOX 4Kx,
  PowerDIN 4PZ, PowerPDU 8QS, and newer metered models.

The integration auto-detects metering support from the JSON response.
Sensors are only created for values the device actually reports.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import logging

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfFrequency,
    UnitOfPower,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import NetioConfigEntry, NetioCoordinator
from .entity import NetioEntity

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class NetioOutputSensorDescription(SensorEntityDescription):
    """Describes a sensor for a single NETIO output."""

    value_fn: Callable
    available_fn: Callable


# Per-output sensor definitions.
# Only created when the device reports the respective value.
OUTPUT_SENSORS: tuple[NetioOutputSensorDescription, ...] = (
    NetioOutputSensorDescription(
        key="current",
        translation_key="current",
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricCurrent.MILLIAMPERE,
        value_fn=lambda o: o.current,
        available_fn=lambda o: o.current is not None,
    ),
    NetioOutputSensorDescription(
        key="load",
        translation_key="load",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.WATT,
        value_fn=lambda o: o.load,
        available_fn=lambda o: o.load is not None,
    ),
    NetioOutputSensorDescription(
        key="energy",
        translation_key="energy",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        value_fn=lambda o: o.energy,
        available_fn=lambda o: o.energy is not None,
    ),
    NetioOutputSensorDescription(
        key="power_factor",
        translation_key="power_factor",
        device_class=SensorDeviceClass.POWER_FACTOR,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda o: o.power_factor,
        available_fn=lambda o: o.power_factor is not None,
    ),
    NetioOutputSensorDescription(
        key="reverse_energy",
        translation_key="reverse_energy",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        value_fn=lambda o: o.reverse_energy,
        available_fn=lambda o: o.reverse_energy is not None,
    ),
)


@dataclass(frozen=True, kw_only=True)
class NetioGlobalSensorDescription(SensorEntityDescription):
    """Describes a sensor for global device measurements."""

    value_fn: Callable
    available_fn: Callable


# Global sensor definitions (one per device).
GLOBAL_SENSORS: tuple[NetioGlobalSensorDescription, ...] = (
    NetioGlobalSensorDescription(
        key="voltage",
        translation_key="voltage",
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        value_fn=lambda gm: gm.voltage,
        available_fn=lambda gm: gm.voltage is not None,
    ),
    NetioGlobalSensorDescription(
        key="frequency",
        translation_key="frequency",
        device_class=SensorDeviceClass.FREQUENCY,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfFrequency.HERTZ,
        value_fn=lambda gm: gm.frequency,
        available_fn=lambda gm: gm.frequency is not None,
    ),
    NetioGlobalSensorDescription(
        key="total_current",
        translation_key="total_current",
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricCurrent.MILLIAMPERE,
        value_fn=lambda gm: gm.total_current,
        available_fn=lambda gm: gm.total_current is not None,
    ),
    NetioGlobalSensorDescription(
        key="total_load",
        translation_key="total_load",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.WATT,
        value_fn=lambda gm: gm.total_load,
        available_fn=lambda gm: gm.total_load is not None,
    ),
    NetioGlobalSensorDescription(
        key="total_energy",
        translation_key="total_energy",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        value_fn=lambda gm: gm.total_energy,
        available_fn=lambda gm: gm.total_energy is not None,
    ),
    NetioGlobalSensorDescription(
        key="total_power_factor",
        translation_key="total_power_factor",
        device_class=SensorDeviceClass.POWER_FACTOR,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda gm: gm.overall_power_factor or gm.total_power_factor,
        available_fn=lambda gm: (
            gm.overall_power_factor is not None or gm.total_power_factor is not None
        ),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: NetioConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up NETIO sensors from a config entry."""
    coordinator: NetioCoordinator = entry.runtime_data
    entities: list[SensorEntity] = []

    # Per-output sensors: only create for outputs that report metering
    for output in coordinator.data.outputs:
        for desc in OUTPUT_SENSORS:
            if desc.available_fn(output):
                entities.append(
                    NetioOutputSensor(coordinator, output.id, desc)
                )

    # Global sensors: only create if device reports global metering
    if coordinator.has_global_metering:
        for desc in GLOBAL_SENSORS:
            if desc.available_fn(coordinator.data.global_measure):
                entities.append(NetioGlobalSensor(coordinator, desc))

    # Digital input S0 counters
    for inp in coordinator.data.inputs:
        entities.append(NetioInputCounterSensor(coordinator, inp.id))

    async_add_entities(entities)


class NetioOutputSensor(NetioEntity, SensorEntity):
    """Sensor for a single NETIO output measurement."""

    entity_description: NetioOutputSensorDescription

    def __init__(
        self,
        coordinator: NetioCoordinator,
        output_id: int,
        description: NetioOutputSensorDescription,
    ) -> None:
        """Initialize the output sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._output_id = output_id
        self._attr_unique_id = (
            f"{coordinator.device_serial}_output_{output_id}_{description.key}"
        )

    @property
    def _output(self):
        """Get the current output data."""
        if self.coordinator.data:
            for output in self.coordinator.data.outputs:
                if output.id == self._output_id:
                    return output
        return None

    @property
    def name(self) -> str | None:
        """Return the sensor name including the output name."""
        output = self._output
        output_name = output.name if output else f"Output {self._output_id}"
        return f"{output_name} {self.entity_description.key}"

    @property
    def native_value(self):
        """Return the sensor value."""
        output = self._output
        if output is None:
            return None
        return self.entity_description.value_fn(output)


class NetioGlobalSensor(NetioEntity, SensorEntity):
    """Sensor for a global device measurement."""

    entity_description: NetioGlobalSensorDescription

    def __init__(
        self,
        coordinator: NetioCoordinator,
        description: NetioGlobalSensorDescription,
    ) -> None:
        """Initialize the global sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = (
            f"{coordinator.device_serial}_{description.key}"
        )

    @property
    def name(self) -> str | None:
        """Return the sensor name."""
        return self.entity_description.key.replace("_", " ").title()

    @property
    def native_value(self):
        """Return the sensor value."""
        if not self.coordinator.data:
            return None
        return self.entity_description.value_fn(
            self.coordinator.data.global_measure
        )


class NetioInputCounterSensor(NetioEntity, SensorEntity):
    """Sensor for a NETIO digital input S0 pulse counter.

    Per JSON API documentation, digital inputs provide:
    - State: 0=open/ON, 1=closed/OFF
    - S0Counter: Number of S0 impulses (not resettable via API)
    """

    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_icon = "mdi:counter"

    def __init__(
        self, coordinator: NetioCoordinator, input_id: int
    ) -> None:
        """Initialize the input counter sensor."""
        super().__init__(coordinator)
        self._input_id = input_id
        self._attr_unique_id = (
            f"{coordinator.device_serial}_input_{input_id}_s0counter"
        )

    @property
    def _input(self):
        """Get the current input data."""
        if self.coordinator.data:
            for inp in self.coordinator.data.inputs:
                if inp.id == self._input_id:
                    return inp
        return None

    @property
    def name(self) -> str | None:
        """Return the sensor name."""
        inp = self._input
        input_name = inp.name if inp else f"Input {self._input_id}"
        return f"{input_name} S0 counter"

    @property
    def native_value(self) -> int | None:
        """Return the counter value."""
        inp = self._input
        if inp is None:
            return None
        return inp.s0_counter
