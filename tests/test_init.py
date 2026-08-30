"""Tests for NETIO integration setup, unload, migration and card registration."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from homeassistant.config_entries import ConfigEntryState
from homeassistant.helpers import device_registry as dr, entity_registry as er

import custom_components.netio_products as init_module
from custom_components.netio_products import (
    _register_card,
    async_migrate_entry,
)
from custom_components.netio_products.const import DOMAIN

from pytest_homeassistant_custom_component.common import MockConfigEntry

from .conftest import TEST_HOST, TEST_SERIAL


async def test_setup_and_unload(hass, config_entry, setup_integration) -> None:
    """Full setup creates devices and unload cleans up."""
    assert config_entry.state is ConfigEntryState.LOADED
    coordinator = config_entry.runtime_data

    dev_reg = dr.async_get(hass)
    parent = dev_reg.async_get_device_by_identifier(
        (DOMAIN, TEST_SERIAL), config_entry.entry_id
    )
    assert parent is not None
    assert coordinator.parent_device_id == parent.id
    assert parent.name == "My NETIO"
    assert parent.manufacturer == "NETIO products a.s."
    assert parent.model == "PowerBOX 4KF"
    assert parent.sw_version == "3.1.2"
    assert parent.serial_number == TEST_SERIAL
    assert parent.configuration_url == f"http://{TEST_HOST}"

    # Sub-devices per output, linked via via_device_id
    sub1 = dev_reg.async_get_device_by_identifier(
        (DOMAIN, f"{TEST_SERIAL}_output_1"), config_entry.entry_id
    )
    sub2 = dev_reg.async_get_device_by_identifier(
        (DOMAIN, f"{TEST_SERIAL}_output_2"), config_entry.entry_id
    )
    assert sub1 is not None
    assert sub1.via_device_id == parent.id
    assert sub1.name == "My NETIO Lamp"
    assert sub2 is not None
    assert sub2.via_device_id == parent.id
    assert sub2.name == "My NETIO Fan"

    assert await hass.config_entries.async_unload(config_entry.entry_id)
    await hass.async_block_till_done()
    assert config_entry.state is ConfigEntryState.NOT_LOADED


async def test_setup_ssl(hass, config_entry, mock_client) -> None:
    """SSL setup builds an https base URL and skips verification."""
    config_entry.add_to_hass(hass)
    hass.config_entries.async_update_entry(
        config_entry, data={**config_entry.data, "use_ssl": True, "port": 443}
    )
    with patch(
        "custom_components.netio_products.NetioApiClient",
        return_value=mock_client,
    ) as mock_cls:
        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

    assert mock_cls.call_args.kwargs["base_url"] == f"https://{TEST_HOST}:443"


async def test_setup_updates_configuration_url(
    hass, config_entry, mock_client, device_state
) -> None:
    """A stale configuration_url is force-updated after platform setup."""
    from homeassistant.helpers.device_registry import DeviceInfo

    stale_info = DeviceInfo(
        identifiers={(DOMAIN, TEST_SERIAL)},
        name="My NETIO",
        manufacturer="NETIO products a.s.",
        configuration_url="http://old.example",
    )
    config_entry.add_to_hass(hass)
    with (
        patch(
            "custom_components.netio_products.NetioApiClient",
            return_value=mock_client,
        ),
        patch(
            "custom_components.netio_products.build_device_info",
            return_value=stale_info,
        ),
        patch(
            "custom_components.netio_products.entity.build_device_info",
            return_value=stale_info,
        ),
    ):
        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

    dev_reg = dr.async_get(hass)
    parent = dev_reg.async_get_device_by_identifier(
        (DOMAIN, TEST_SERIAL), config_entry.entry_id
    )
    assert parent.configuration_url == f"http://{TEST_HOST}"


async def test_migrate_entry_v1_to_v2(hass, config_entry) -> None:
    """v1→v2 converts integration-disabled buttons to hidden."""
    config_entry.add_to_hass(hass)
    hass.config_entries.async_update_entry(config_entry, version=1)

    ent_reg = er.async_get(hass)
    disabled_button = ent_reg.async_get_or_create(
        "button",
        DOMAIN,
        f"{TEST_SERIAL}_output_1_restart",
        config_entry=config_entry,
        disabled_by=er.RegistryEntryDisabler.INTEGRATION,
    )
    user_disabled_button = ent_reg.async_get_or_create(
        "button",
        DOMAIN,
        f"{TEST_SERIAL}_output_1_toggle",
        config_entry=config_entry,
        disabled_by=er.RegistryEntryDisabler.USER,
    )
    enabled_button = ent_reg.async_get_or_create(
        "button",
        DOMAIN,
        f"{TEST_SERIAL}_output_1_short_on",
        config_entry=config_entry,
    )
    switch = ent_reg.async_get_or_create(
        "switch",
        DOMAIN,
        f"{TEST_SERIAL}_output_1",
        config_entry=config_entry,
        disabled_by=er.RegistryEntryDisabler.INTEGRATION,
    )

    assert await async_migrate_entry(hass, config_entry)
    assert config_entry.version == 2

    migrated = ent_reg.async_get(disabled_button.entity_id)
    assert migrated.disabled_by is None
    assert migrated.hidden_by is er.RegistryEntryHider.INTEGRATION

    # User-disabled entities are left untouched
    untouched = ent_reg.async_get(user_disabled_button.entity_id)
    assert untouched.disabled_by is er.RegistryEntryDisabler.USER
    assert untouched.hidden_by is None

    # Buttons that were not disabled stay as-is
    unchanged = ent_reg.async_get(enabled_button.entity_id)
    assert unchanged.disabled_by is None
    assert unchanged.hidden_by is None

    # Non-button entities are skipped even if integration-disabled
    switch_after = ent_reg.async_get(switch.entity_id)
    assert switch_after.disabled_by is er.RegistryEntryDisabler.INTEGRATION
    assert switch_after.hidden_by is None


async def test_migrate_entry_v2_noop(hass, config_entry) -> None:
    """A current-version entry migrates as a no-op."""
    config_entry.add_to_hass(hass)
    assert await async_migrate_entry(hass, config_entry)
    assert config_entry.version == 2


async def test_migrate_entry_future_version(hass) -> None:
    """Downgrading from a future version is not supported."""
    entry = MockConfigEntry(domain=DOMAIN, version=3)
    entry.add_to_hass(hass)
    assert not await async_migrate_entry(hass, entry)


@pytest.fixture
def reset_card_registered(monkeypatch):
    """Ensure the module-level card registration flag starts False."""
    monkeypatch.setattr(init_module, "_CARD_REGISTERED", False)


async def test_register_card_already_registered(
    hass, monkeypatch
) -> None:
    """A second call is a no-op."""
    monkeypatch.setattr(init_module, "_CARD_REGISTERED", True)
    hass.http = MagicMock()
    await _register_card(hass)
    hass.http.async_register_static_paths.assert_not_called()


async def test_register_card_missing_file(hass, reset_card_registered) -> None:
    """A missing card file marks registration done without side effects."""
    hass.http = MagicMock()
    with patch.object(Path, "exists", return_value=False):
        await _register_card(hass)
    assert init_module._CARD_REGISTERED is True
    hass.http.async_register_static_paths.assert_not_called()


async def test_register_card_creates_resource(
    hass, reset_card_registered
) -> None:
    """Static path and a new Lovelace resource are registered."""
    hass.http = MagicMock()
    hass.http.async_register_static_paths = AsyncMock()

    resources = MagicMock()
    resources.loaded = True
    resources.async_items.return_value = [{"id": "x", "url": "/other.js"}]
    resources.async_create_item = AsyncMock()
    resources.async_update_item = AsyncMock()
    hass.data["lovelace"] = MagicMock(resources=resources)

    await _register_card(hass)

    hass.http.async_register_static_paths.assert_awaited_once()
    resources.async_create_item.assert_awaited_once()
    created = resources.async_create_item.call_args.args[0]
    assert created["res_type"] == "module"
    assert created["url"].startswith("/netio_products/netio-card.js?v=")
    resources.async_update_item.assert_not_called()
    assert init_module._CARD_REGISTERED is True


async def test_register_card_updates_existing_resource(
    hass, reset_card_registered
) -> None:
    """An existing resource with an old version gets its URL updated."""
    hass.http = MagicMock()
    hass.http.async_register_static_paths = AsyncMock()

    resources = MagicMock()
    resources.loaded = True
    existing = {"id": "abc", "url": "/netio_products/netio-card.js?v=0.0.1"}
    resources.async_items.return_value = [existing]
    resources.async_create_item = AsyncMock()
    resources.async_update_item = AsyncMock()
    hass.data["lovelace"] = MagicMock(resources=resources)

    await _register_card(hass)

    resources.async_update_item.assert_awaited_once()
    assert resources.async_update_item.call_args.args[0] == "abc"
    resources.async_create_item.assert_not_called()


async def test_register_card_existing_resource_up_to_date(
    hass, reset_card_registered
) -> None:
    """An existing resource with the current URL is left alone."""
    import json

    manifest = Path(init_module.__file__).parent / "manifest.json"
    version = json.loads(manifest.read_text())["version"]

    hass.http = MagicMock()
    hass.http.async_register_static_paths = AsyncMock()

    resources = MagicMock()
    resources.loaded = True
    existing = {"id": "abc", "url": f"/netio_products/netio-card.js?v={version}"}
    resources.async_items.return_value = [existing]
    resources.async_create_item = AsyncMock()
    resources.async_update_item = AsyncMock()
    hass.data["lovelace"] = MagicMock(resources=resources)

    await _register_card(hass)

    resources.async_update_item.assert_not_called()
    resources.async_create_item.assert_not_called()


async def test_register_card_resources_not_loaded(
    hass, reset_card_registered
) -> None:
    """Unloaded Lovelace resources are skipped."""
    hass.http = MagicMock()
    hass.http.async_register_static_paths = AsyncMock()

    resources = MagicMock()
    resources.loaded = False
    resources.async_create_item = AsyncMock()
    hass.data["lovelace"] = MagicMock(resources=resources)

    await _register_card(hass)
    resources.async_create_item.assert_not_called()
    assert init_module._CARD_REGISTERED is True


async def test_register_card_manifest_read_error(
    hass, reset_card_registered
) -> None:
    """A manifest read error falls back to version 0."""
    hass.http = MagicMock()
    hass.http.async_register_static_paths = AsyncMock()

    resources = MagicMock()
    resources.loaded = True
    resources.async_items.return_value = []
    resources.async_create_item = AsyncMock()
    hass.data["lovelace"] = MagicMock(resources=resources)

    with patch.object(Path, "read_text", side_effect=OSError):
        await _register_card(hass)

    created = resources.async_create_item.call_args.args[0]
    assert created["url"] == "/netio_products/netio-card.js?v=0"


async def test_register_card_static_path_runtime_error(
    hass, reset_card_registered
) -> None:
    """A RuntimeError from the modern static path API is tolerated."""
    hass.http = MagicMock()
    hass.http.async_register_static_paths = AsyncMock(
        side_effect=RuntimeError("already registered")
    )
    await _register_card(hass)
    assert init_module._CARD_REGISTERED is True


async def test_register_card_legacy_static_path(
    hass, reset_card_registered
) -> None:
    """AttributeError on the modern API falls back to the legacy one."""
    hass.http = MagicMock()
    hass.http.async_register_static_paths = AsyncMock(
        side_effect=AttributeError
    )
    await _register_card(hass)
    hass.http.register_static_path.assert_called_once()
    assert init_module._CARD_REGISTERED is True


async def test_register_card_legacy_static_path_fails(
    hass, reset_card_registered
) -> None:
    """A failing legacy static path registration is tolerated."""
    hass.http = MagicMock()
    hass.http.async_register_static_paths = AsyncMock(
        side_effect=AttributeError
    )
    hass.http.register_static_path = MagicMock(side_effect=RuntimeError)
    await _register_card(hass)
    assert init_module._CARD_REGISTERED is True


async def test_register_card_lovelace_error(
    hass, reset_card_registered
) -> None:
    """Errors while touching Lovelace resources are swallowed."""
    hass.http = MagicMock()
    hass.http.async_register_static_paths = AsyncMock()

    resources = MagicMock()
    resources.loaded = True
    resources.async_items.side_effect = ValueError("broken")
    hass.data["lovelace"] = MagicMock(resources=resources)

    await _register_card(hass)
    assert init_module._CARD_REGISTERED is True
