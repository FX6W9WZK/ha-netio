"""The NETIO integration.

Integrates NETIO networked power sockets/PDUs with Home Assistant
using the NETIO JSON over HTTP(s) M2M API protocol (Version 2.4).

Supported devices (per NETIO documentation):
  Current: PowerCable 1Kx/2KB/2PZ/2KZ/2PB, PowerBOX 3Px/4Kx,
           PowerDIN 4PZ/ZK3/ZP3, PowerPDU 4PS/4KS/4PV/4KB/4PB/
           8QV/8QS/8KS/8KF/8QB/8KB, PowerPDU VK6/FK6
  Obsolete: PowerPDU 4C, NETIO 4, NETIO 4All

Protocol: JSON over HTTP(s) POST/GET to /netio.json
"""

from __future__ import annotations

import logging
from pathlib import Path

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_PORT, CONF_USERNAME, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import NetioApiClient
from .const import DOMAIN
from .coordinator import NetioCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.SWITCH,
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
]

_CARD_REGISTERED = False


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up NETIO from a config entry."""
    global _CARD_REGISTERED
    if not _CARD_REGISTERED:
        card_path = Path(__file__).parent / "www" / "netio-card.js"
        if card_path.exists():
            hass.http.register_static_path(
                "/netio/netio-card.js",
                str(card_path),
                cache_headers=False,
            )
            _CARD_REGISTERED = True

    host = entry.data[CONF_HOST]
    port = entry.data[CONF_PORT]
    username = entry.data[CONF_USERNAME]
    password = entry.data[CONF_PASSWORD]
    use_ssl = entry.data.get("use_ssl", False)

    scheme = "https" if use_ssl else "http"
    base_url = f"{scheme}://{host}:{port}"

    session = async_get_clientsession(hass, verify_ssl=False)
    client = NetioApiClient(
        base_url=base_url,
        username=username,
        password=password,
        session=session,
        verify_ssl=not use_ssl,
    )

    coordinator = NetioCoordinator(hass, client, entry)
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a NETIO config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
