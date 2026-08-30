"""Data update coordinator for NETIO devices."""

from __future__ import annotations

from datetime import timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import (
    NetioAgent,
    NetioApiClient,
    NetioApiError,
    NetioAuthError,
    NetioConnectionError,
    NetioDeviceState,
)
from .const import DEFAULT_SCAN_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)

type NetioConfigEntry = ConfigEntry[NetioCoordinator]


def compute_serial(agent: NetioAgent, fallback: str) -> str:
    """Compute the device serial (unique identifier).

    Per JSON API doc: SerialNumber is identical with the label on
    the delivery box. Prefer SerialNumber over MAC when available.
    """
    if agent.serial_number:
        return agent.serial_number
    if agent.mac:
        return agent.mac.replace(":", "")
    return fallback


def build_device_info(coordinator: NetioCoordinator) -> DeviceInfo:
    """Build the DeviceInfo for the parent NETIO device."""
    agent = coordinator.data.agent
    serial = coordinator.device_serial
    return DeviceInfo(
        identifiers={(DOMAIN, serial)},
        name=agent.device_name or agent.model or "NETIO Device",
        manufacturer="NETIO products a.s.",
        model=agent.model,
        sw_version=agent.version,
        serial_number=serial,
        configuration_url=coordinator.client.web_url,
    )


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
        # Registry id of the parent device; set during setup before the
        # platforms are forwarded, used for via_device_id links.
        self.parent_device_id: str | None = None
        self._last_device_name: str | None = None
        self._last_output_names: dict[int, str] = {}
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
            state = await self.client.get_state()
        except NetioAuthError as err:
            raise ConfigEntryAuthFailed(f"Authentication failed: {err}") from err
        except NetioConnectionError as err:
            raise UpdateFailed(f"Connection error: {err}") from err
        except NetioApiError as err:
            raise UpdateFailed(f"API error: {err}") from err

        self._update_device_names(state)
        return state

    def _update_device_names(self, state: NetioDeviceState) -> None:
        """Update device registry names if they changed on the NETIO device."""
        from homeassistant.helpers import device_registry as dr

        agent = state.agent
        # Compute serial from the current state, not self.device_serial,
        # because self.data may still be None during first poll.
        serial = compute_serial(agent, self.config_entry.entry_id)
        device_name = agent.device_name or agent.model or "NETIO Device"

        # Check if any name actually changed
        current_output_names: dict[int, str] = {}
        if state.outputs:
            for out in state.outputs:
                current_output_names[out.id] = out.name or f"Output {out.id}"

        if (
            device_name == self._last_device_name
            and current_output_names == self._last_output_names
        ):
            return  # Nothing changed

        dev_reg = dr.async_get(self.hass)

        # Update parent device name
        device_renamed = device_name != self._last_device_name
        if device_renamed:
            device = dev_reg.async_get_device_by_identifier(
                (DOMAIN, serial), self.config_entry.entry_id
            )
            if device and device.name != device_name:
                dev_reg.async_update_device(device.id, name=device_name)
                _LOGGER.debug("Updated device name: %s", device_name)
            self._last_device_name = device_name

        # Update sub-device names (per outlet). Sub-device names embed the
        # device name as prefix, so a device rename must refresh them too.
        for output_id, output_name in current_output_names.items():
            if device_renamed or output_name != self._last_output_names.get(output_id):
                full_name = f"{device_name} {output_name}"
                sub_device = dev_reg.async_get_device_by_identifier(
                    (DOMAIN, f"{serial}_output_{output_id}"),
                    self.config_entry.entry_id,
                )
                if sub_device and sub_device.name != full_name:
                    dev_reg.async_update_device(sub_device.id, name=full_name)
                    _LOGGER.debug(
                        "Updated output %d name: %s", output_id, full_name
                    )

        self._last_output_names = current_output_names

    @property
    def device_serial(self) -> str:
        """Return the device serial number (unique identifier).

        Per JSON API doc: SerialNumber is identical with the label on
        the delivery box. Prefer SerialNumber over MAC when available.
        """
        if self.data:
            return compute_serial(self.data.agent, self.config_entry.entry_id)
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
