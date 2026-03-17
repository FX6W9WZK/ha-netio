"""Base entities for NETIO integration.

Two base classes:
- NetioEntity: for device-level entities (global sensors, digital inputs).
  Registered under the main NETIO device.
- NetioOutputEntity: for per-outlet entities (switch, per-output sensors, buttons).
  Each outlet is registered as its own sub-device via `via_device`,
  so outlets can be assigned to different rooms in Home Assistant.
"""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import NetioCoordinator


class NetioEntity(CoordinatorEntity[NetioCoordinator]):
    """Base class for device-level NETIO entities.

    Use this for entities that belong to the NETIO device as a whole:
    global sensors (voltage, frequency, total load, ...),
    digital input binary sensors, and input S0 counters.
    """

    _attr_has_entity_name = True

    def __init__(self, coordinator: NetioCoordinator) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)
        agent = coordinator.data.agent

        # Per JSON API documentation:
        # - SerialNumber is the preferred unique identifier
        # - MAC may differ from SerialNumber on some devices
        serial = coordinator.device_serial

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, serial)},
            name=agent.device_name or agent.model or "NETIO Device",
            manufacturer="NETIO products a.s.",
            model=agent.model,
            sw_version=agent.version,
            serial_number=serial,
            configuration_url=coordinator.client.web_url,
        )


class NetioOutputEntity(CoordinatorEntity[NetioCoordinator]):
    """Base class for per-outlet NETIO entities.

    Each power output is registered as a sub-device of the main
    NETIO device. This allows assigning individual outlets to
    different rooms in Home Assistant.

    The sub-device uses `via_device` to link back to the parent.
    """

    _attr_has_entity_name = True

    def __init__(self, coordinator: NetioCoordinator, output_id: int) -> None:
        """Initialize the per-outlet entity.

        Args:
            coordinator: The data update coordinator.
            output_id: 1-based output ID from the NETIO device.
        """
        super().__init__(coordinator)
        self._output_id = output_id
        agent = coordinator.data.agent
        serial = coordinator.device_serial

        # Resolve the output name from current data
        output_name = f"Output {output_id}"
        if coordinator.data and coordinator.data.outputs:
            for out in coordinator.data.outputs:
                if out.id == output_id and out.name:
                    output_name = out.name
                    break

        device_name = agent.device_name or agent.model or "NETIO Device"

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{serial}_output_{output_id}")},
            name=f"{device_name} {output_name}",
            manufacturer="NETIO products a.s.",
            model=agent.model,
            sw_version=agent.version,
            via_device=(DOMAIN, serial),
        )
