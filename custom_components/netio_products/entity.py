"""Base entities for NETIO integration.

Two base classes:
- NetioEntity: for device-level entities (global sensors, digital inputs).
  Registered under the main NETIO device.
- NetioOutputEntity: for per-outlet entities (switch, per-output sensors, buttons).
  Each outlet is registered as its own sub-device linked to the parent,
  so outlets can be assigned to different rooms in Home Assistant.
"""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import NetioCoordinator, build_device_info


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

        # Per JSON API documentation:
        # - SerialNumber is the preferred unique identifier
        # - MAC may differ from SerialNumber on some devices
        self._attr_device_info = build_device_info(coordinator)


class NetioOutputEntity(CoordinatorEntity[NetioCoordinator]):
    """Base class for per-outlet NETIO entities.

    Each power output is registered as a sub-device of the main
    NETIO device. This allows assigning individual outlets to
    different rooms in Home Assistant.

    The sub-device uses `via_device_id` to link back to the parent.
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

        device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{serial}_output_{output_id}")},
            name=f"{device_name} {output_name}",
            manufacturer="NETIO products a.s.",
            model=agent.model,
            sw_version=agent.version,
        )
        if coordinator.parent_device_id is not None:
            device_info["via_device_id"] = coordinator.parent_device_id
        self._attr_device_info = device_info
