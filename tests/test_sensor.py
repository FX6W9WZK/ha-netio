"""Tests for the NETIO sensor platform."""
from __future__ import annotations

from homeassistant.const import STATE_UNKNOWN
from homeassistant.helpers import entity_registry as er

from custom_components.netio_products.const import DOMAIN

from .conftest import TEST_SERIAL, make_output, make_state


def sensor_entity_id(hass, unique_suffix: str) -> str | None:
    """Resolve a sensor entity id from its unique id."""
    ent_reg = er.async_get(hass)
    return ent_reg.async_get_entity_id(
        "sensor", DOMAIN, f"{TEST_SERIAL}_{unique_suffix}"
    )


async def test_output_sensors(hass, config_entry, setup_integration) -> None:
    """Metered outputs get one sensor per reported value."""
    expected = {
        "output_1_current": "120",
        "output_1_load": "25",
        "output_1_energy": "1000",
        "output_1_power_factor": "0.95",
        "output_1_reverse_energy": "5",
    }
    for suffix, value in expected.items():
        entity_id = sensor_entity_id(hass, suffix)
        assert entity_id, f"missing sensor for {suffix}"
        assert hass.states.get(entity_id).state == value

    # The unmetered output gets no sensors at all
    for key in ("current", "load", "energy", "power_factor", "reverse_energy"):
        assert sensor_entity_id(hass, f"output_2_{key}") is None


async def test_global_sensors(hass, config_entry, setup_integration) -> None:
    """Global measurements are exposed as device-level sensors."""
    expected = {
        "voltage": "230.1",
        "frequency": "50.0",
        "total_current": "250",
        "total_load": "57",
        "total_energy": "123456",
        "total_power_factor": "0.9",
    }
    for suffix, value in expected.items():
        entity_id = sensor_entity_id(hass, suffix)
        assert entity_id, f"missing global sensor {suffix}"
        assert hass.states.get(entity_id).state == value


async def test_input_counter_sensors(hass, config_entry, setup_integration) -> None:
    """Digital inputs expose their S0 pulse counters."""
    entity_id_1 = sensor_entity_id(hass, "input_1_s0counter")
    entity_id_2 = sensor_entity_id(hass, "input_2_s0counter")
    assert hass.states.get(entity_id_1).state == "42"
    assert hass.states.get(entity_id_2).state == "7"

    # Input names feed the translation placeholders / friendly names
    state = hass.states.get(entity_id_1)
    assert "Door" in state.attributes["friendly_name"]


async def test_no_metering_no_sensors(hass, config_entry, mock_client) -> None:
    """Without metering data, only input counters are created."""
    from unittest.mock import patch

    mock_client.get_state.return_value = make_state(
        outputs=[
            make_output(1, "Lamp", 1, metered=False),
            make_output(2, "Fan", 0, metered=False),
        ],
        with_global=False,
        inputs=[],
    )
    config_entry.add_to_hass(hass)
    with patch(
        "custom_components.netio_products.NetioApiClient",
        return_value=mock_client,
    ):
        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

    ent_reg = er.async_get(hass)
    sensors = [
        e
        for e in er.async_entries_for_config_entry(ent_reg, config_entry.entry_id)
        if e.domain == "sensor"
    ]
    assert sensors == []


async def test_total_power_factor_fallback(hass, config_entry, mock_client) -> None:
    """The overall power factor falls back to TotalPowerFactor."""
    from unittest.mock import patch

    state = make_state()
    state.global_measure.overall_power_factor = None
    state.global_measure.total_power_factor = 0.85
    mock_client.get_state.return_value = state

    config_entry.add_to_hass(hass)
    with patch(
        "custom_components.netio_products.NetioApiClient",
        return_value=mock_client,
    ):
        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

    entity_id = sensor_entity_id(hass, "total_power_factor")
    assert hass.states.get(entity_id).state == "0.85"


async def test_sensors_unknown_when_data_missing(
    hass, config_entry, setup_integration
) -> None:
    """Sensors report unknown when their source data disappears."""
    coordinator = config_entry.runtime_data
    output_sensor = sensor_entity_id(hass, "output_1_current")
    input_sensor = sensor_entity_id(hass, "input_1_s0counter")
    global_sensor = sensor_entity_id(hass, "voltage")

    coordinator.async_set_updated_data(
        make_state(outputs=[], inputs=[], with_global=False)
    )
    await hass.async_block_till_done()

    assert hass.states.get(output_sensor).state == STATE_UNKNOWN
    assert hass.states.get(input_sensor).state == STATE_UNKNOWN
    assert hass.states.get(global_sensor).state == STATE_UNKNOWN

    # Fully missing coordinator data is also handled
    coordinator.async_set_updated_data(None)
    await hass.async_block_till_done()
    assert hass.states.get(global_sensor).state == STATE_UNKNOWN
    assert hass.states.get(output_sensor).state == STATE_UNKNOWN
