"""Data update coordinator for NETIO devices."""

from __future__ import annotations

from datetime import timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import (
    NetioApiClient,
    NetioApiError,
    NetioAuthError,
    NetioConnectionError,
    NetioDeviceState,
)
from .const import DEFAULT_SCAN_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)

type NetioConfigEntry = ConfigEntry[NetioCoordinator]


class NetioCoordinator(DataUpdateCoordinator[NetioDeviceState]):
    """Coordinator to manage fetching NETIO device state.

    Polls the device via JSON API GET at a regular interval.
    """

    config_entry: NetioConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        client: NetioApiClient,
        config_entry: NetioConfigEntry,
    ) -> None:
        """Initialize the coordinator."""
        self.client = client
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{config_entry.entry_id}",
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
            config_entry=config_entry,
        )

    async def _async_update_data(self) -> NetioDeviceState:
        """Fetch state from the NETIO device."""
        try:
            return await self.client.get_state()
        except NetioAuthError as err:
            raise UpdateFailed(f"Authentication failed: {err}") from err
        except NetioConnectionError as err:
            raise UpdateFailed(f"Connection error: {err}") from err
        except NetioApiError as err:
            raise UpdateFailed(f"API error: {err}") from err

    @property
    def device_serial(self) -> str:
        """Return the device serial number (unique identifier).

        Per JSON API doc: SerialNumber is identical with the label on
        the delivery box. Prefer SerialNumber over MAC when available.
        """
        if self.data and self.data.agent.serial_number:
            return self.data.agent.serial_number
        if self.data and self.data.agent.mac:
            return self.data.agent.mac.replace(":", "")
        return self.config_entry.entry_id

    @property
    def has_metering(self) -> bool:
        """Return True if device reports energy metering data.

        Auto-detected from the JSON response: if any output has
        a 'Current' field, the device supports metering.
        """
        if not self.data or not self.data.outputs:
            return False
        return any(o.current is not None for o in self.data.outputs)

    @property
    def has_global_metering(self) -> bool:
        """Return True if device reports global metering data."""
        if not self.data:
            return False
        return self.data.global_measure.voltage is not None

    @property
    def has_inputs(self) -> bool:
        """Return True if device has digital inputs."""
        return bool(self.data and self.data.inputs)
