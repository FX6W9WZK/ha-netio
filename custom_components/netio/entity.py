"""Base entity for NETIO integration."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import NetioCoordinator


class NetioEntity(CoordinatorEntity[NetioCoordinator]):
    """Base class for NETIO entities."""

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
            configuration_url=coordinator.client._base_url,
        )
