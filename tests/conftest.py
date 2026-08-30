"""Shared fixtures for the NETIO test suite."""
from __future__ import annotations

from unittest.mock import patch

import pytest


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Load custom_components from this repository."""
    yield


@pytest.fixture
def mock_setup_entry():
    """Prevent the integration from actually being set up."""
    with patch(
        "custom_components.netio_products.async_setup_entry", return_value=True
    ) as mock:
        yield mock


# --- Extended fixtures for the full test suite (appended) ---

from unittest.mock import AsyncMock, MagicMock

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.netio_products.api import (
    NetioAgent,
    NetioDeviceState,
    NetioGlobalMeasure,
    NetioInput,
    NetioOutput,
)
from custom_components.netio_products.const import (
    CONF_ENABLE_RESTART,
    CONF_ENABLE_SHORT_ON,
    CONF_ENABLE_TOGGLE,
    DOMAIN,
)

TEST_SERIAL = "24A42C123456"
TEST_HOST = "192.168.1.50"


def make_output(
    output_id: int = 1,
    name: str = "Lamp",
    state: int = 1,
    metered: bool = True,
    **overrides,
) -> NetioOutput:
    """Build a NetioOutput for tests."""
    data = dict(id=output_id, name=name, state=state, action=6, delay=5000)
    if metered:
        data.update(
            current=120,
            power_factor=0.95,
            phase=0.0,
            load=25,
            energy=1000,
            energy_nr=1100,
            reverse_energy=5,
            reverse_energy_nr=6,
        )
    data.update(overrides)
    return NetioOutput(**data)


def make_state(
    device_name: str = "My NETIO",
    model: str = "PowerBOX 4KF",
    serial: str = TEST_SERIAL,
    mac: str = "24:A4:2C:12:34:56",
    outputs: list[NetioOutput] | None = None,
    inputs: list[NetioInput] | None = None,
    with_global: bool = True,
) -> NetioDeviceState:
    """Build a complete NetioDeviceState for tests."""
    if outputs is None:
        outputs = [
            make_output(1, "Lamp", 1, metered=True),
            make_output(2, "Fan", 0, metered=False),
        ]
    if inputs is None:
        inputs = [
            NetioInput(id=1, name="Door", state=0, s0_counter=42),
            NetioInput(id=2, name="Window", state=1, s0_counter=7),
        ]
    agent = NetioAgent(
        model=model,
        version="3.1.2",
        json_ver="2.4",
        device_name=device_name,
        mac=mac,
        serial_number=serial,
        uptime=100,
        num_outputs=len(outputs),
        num_inputs=len(inputs),
    )
    gm = NetioGlobalMeasure()
    if with_global:
        gm = NetioGlobalMeasure(
            voltage=230.1,
            frequency=50.0,
            total_current=250,
            overall_power_factor=0.9,
            total_load=57,
            total_energy=123456,
        )
    return NetioDeviceState(
        agent=agent, global_measure=gm, outputs=outputs, inputs=inputs
    )


@pytest.fixture
def device_state() -> NetioDeviceState:
    """Default full-featured device state."""
    return make_state()


@pytest.fixture
def mock_client(device_state: NetioDeviceState) -> MagicMock:
    """Mocked NetioApiClient instance."""
    client = MagicMock()
    client.get_state = AsyncMock(return_value=device_state)
    client.set_output = AsyncMock(return_value=device_state)
    client.web_url = f"http://{TEST_HOST}"
    return client


@pytest.fixture
def config_entry() -> MockConfigEntry:
    """A config entry as created by the config flow."""
    return MockConfigEntry(
        domain=DOMAIN,
        title="My NETIO",
        unique_id=TEST_SERIAL,
        version=2,
        data={
            "host": TEST_HOST,
            "port": 80,
            "username": "netio",
            "password": "netio",
            "use_ssl": False,
        },
        options={
            CONF_ENABLE_RESTART: True,
            CONF_ENABLE_SHORT_ON: True,
            CONF_ENABLE_TOGGLE: True,
        },
    )


@pytest.fixture
async def setup_integration(hass, config_entry, mock_client):
    """Set up the integration with a mocked API client."""
    config_entry.add_to_hass(hass)
    with patch(
        "custom_components.netio_products.NetioApiClient",
        return_value=mock_client,
    ):
        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()
    yield mock_client
