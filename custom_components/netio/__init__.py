"""The NETIO integration."""

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
_CARD_URL_BASE = "/netio/netio-card.js"


async def _register_card(hass: HomeAssistant) -> None:
    """Register the Lovelace card static path and resource."""
    global _CARD_REGISTERED
    if _CARD_REGISTERED:
        return

    card_path = Path(__file__).parent / "www" / "netio-card.js"
    if not card_path.exists():
        _CARD_REGISTERED = True
        return

    # Read version from JS file first line: const CARD_VERSION = "x.y.z";
    version = "0"
    try:
        first_line = card_path.read_text(encoding="utf-8").split("\n", 1)[0]
        if "CARD_VERSION" in first_line:
            version = first_line.split('"')[1]
    except (IndexError, OSError):
        pass

    card_url = f"{_CARD_URL_BASE}?v={version}"

    # 1. Register static path
    try:
        from homeassistant.components.http import StaticPathConfig
        await hass.http.async_register_static_paths(
            [StaticPathConfig(_CARD_URL_BASE, str(card_path), False)]
        )
    except (ImportError, AttributeError):
        try:
            hass.http.register_static_path(
                _CARD_URL_BASE, str(card_path), cache_headers=False
            )
        except (AttributeError, RuntimeError):
            pass
    except RuntimeError:
        pass

    # 2. Auto-register/update Lovelace resource
    try:
        from homeassistant.components.lovelace import DOMAIN as LL_DOMAIN
        from homeassistant.components.lovelace.resources import (
            ResourceStorageCollection,
        )

        ll_data = hass.data.get(LL_DOMAIN)
        if ll_data and hasattr(ll_data, "resources"):
            resources: ResourceStorageCollection = ll_data.resources
            if resources.loaded:
                # Find existing NETIO resource
                existing = None
                for item in resources.async_items():
                    if _CARD_URL_BASE in item.get("url", ""):
                        existing = item
                        break

                if existing:
                    # Update URL with new version if changed
                    if existing["url"] != card_url:
                        await resources.async_update_item(
                            existing["id"], {"url": card_url}
                        )
                        _LOGGER.debug(
                            "Updated NETIO card resource: %s", card_url
                        )
                else:
                    # Create new resource
                    await resources.async_create_item(
                        {"res_type": "module", "url": card_url}
                    )
                    _LOGGER.info(
                        "Registered NETIO card resource: %s", card_url
                    )
    except Exception:  # noqa: BLE001
        # Lovelace resources not available (e.g. YAML mode) — user manages manually
        _LOGGER.debug(
            "Could not auto-register Lovelace resource. "
            "Add manually: %s",
            card_url,
        )

    _CARD_REGISTERED = True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up NETIO from a config entry."""
    await _register_card(hass)

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

    # Explicitly register the parent device BEFORE platform setup.
    # This ensures the parent device exists so sub-devices can reference
    # it via via_device. Without this, if no global entities exist,
    # the parent device would never be created and sub-devices would
    # have via_device_id=null.
    from homeassistant.helpers import device_registry as dr
    dev_reg = dr.async_get(hass)
    serial = coordinator.device_serial
    agent = coordinator.data.agent
    dev_reg.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, serial)},
        name=agent.device_name or agent.model or "NETIO Device",
        manufacturer="NETIO products a.s.",
        model=agent.model,
        sw_version=agent.version,
        serial_number=serial,
        configuration_url=client.web_url,
    )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Force-update configuration_url in device registry (HA caches it)
    device = dev_reg.async_get_device(identifiers={(DOMAIN, serial)})
    if device and device.configuration_url != client.web_url:
        dev_reg.async_update_device(
            device.id, configuration_url=client.web_url
        )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a NETIO config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
