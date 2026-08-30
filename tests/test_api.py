"""Tests for the NETIO JSON API client."""
from __future__ import annotations

import asyncio

import aiohttp
import pytest

from homeassistant.helpers.aiohttp_client import async_get_clientsession

from custom_components.netio_products.api import (
    NetioApiClient,
    NetioApiError,
    NetioAuthError,
    NetioConnectionError,
    _parse_device_state,
)

BASE_URL = "http://192.168.1.99:8080"
API_URL = f"{BASE_URL}/netio.json"

FULL_RESPONSE = {
    "Agent": {
        "Model": "PowerBOX 4KF",
        "Version": "3.1.2",
        "JSONVer": "2.4",
        "DeviceName": "My NETIO",
        "VendorID": 0,
        "OemID": 0,
        "MAC": "24:A4:2C:12:34:56",
        "SerialNumber": "24A42C123456",
        "Uptime": 100,
        "Time": "2024-01-01T00:00:00+01:00",
        "NumOutputs": 2,
        "NumInputs": 1,
    },
    "GlobalMeasure": {
        "Voltage": 230.1,
        "Frequency": 50.0,
        "TotalCurrent": 250,
        "OverallPowerFactor": 0.9,
        "TotalPowerFactor": 0.91,
        "Phase": 1.5,
        "TotalPhase": 1.6,
        "TotalLoad": 57,
        "TotalEnergy": 123456,
        "TotalEnergyNR": 123457,
        "TotalReverseEnergy": 12,
        "TotalReverseEnergyNR": 13,
        "EnergyStart": "2023-01-01T00:00:00+01:00",
    },
    "Outputs": [
        {
            "ID": 1,
            "Name": "Lamp",
            "State": 1,
            "Action": 6,
            "Delay": 5000,
            "Current": 120,
            "PowerFactor": 0.95,
            "Phase": 0.0,
            "Load": 25,
            "Energy": 1000,
            "EnergyNR": 1100,
            "ReverseEnergy": 5,
            "ReverseEnergyNR": 6,
        },
        {"ID": 2, "State": 0},
    ],
    "Inputs": [
        {"ID": 1, "Name": "Door", "State": 1, "S0Counter": 42},
        {"ID": 2},
    ],
}


def _make_client(hass, base_url: str = BASE_URL) -> NetioApiClient:
    return NetioApiClient(
        base_url=base_url,
        username="netio",
        password="netio",
        session=async_get_clientsession(hass),
    )


async def test_get_state_full_parsing(hass, aioclient_mock) -> None:
    """A full response is parsed into all dataclasses."""
    aioclient_mock.get(API_URL, json=FULL_RESPONSE)
    client = _make_client(hass)

    state = await client.get_state()

    agent = state.agent
    assert agent.model == "PowerBOX 4KF"
    assert agent.version == "3.1.2"
    assert agent.json_ver == "2.4"
    assert agent.device_name == "My NETIO"
    assert agent.mac == "24:A4:2C:12:34:56"
    assert agent.serial_number == "24A42C123456"
    assert agent.uptime == 100
    assert agent.time == "2024-01-01T00:00:00+01:00"
    assert agent.num_outputs == 2
    assert agent.num_inputs == 1

    gm = state.global_measure
    assert gm.voltage == 230.1
    assert gm.frequency == 50.0
    assert gm.total_current == 250
    assert gm.overall_power_factor == 0.9
    assert gm.total_power_factor == 0.91
    assert gm.phase == 1.5
    assert gm.total_phase == 1.6
    assert gm.total_load == 57
    assert gm.total_energy == 123456
    assert gm.total_energy_nr == 123457
    assert gm.total_reverse_energy == 12
    assert gm.total_reverse_energy_nr == 13
    assert gm.energy_start == "2023-01-01T00:00:00+01:00"

    assert len(state.outputs) == 2
    out1 = state.outputs[0]
    assert out1.id == 1
    assert out1.name == "Lamp"
    assert out1.state == 1
    assert out1.action == 6
    assert out1.delay == 5000
    assert out1.current == 120
    assert out1.power_factor == 0.95
    assert out1.phase == 0.0
    assert out1.load == 25
    assert out1.energy == 1000
    assert out1.energy_nr == 1100
    assert out1.reverse_energy == 5
    assert out1.reverse_energy_nr == 6

    # Output with minimal fields gets defaults
    out2 = state.outputs[1]
    assert out2.name == "output_2"
    assert out2.state == 0
    assert out2.action == 6
    assert out2.delay == 5000
    assert out2.current is None
    assert out2.load is None

    assert len(state.inputs) == 2
    assert state.inputs[0].name == "Door"
    assert state.inputs[0].state == 1
    assert state.inputs[0].s0_counter == 42
    # Input with minimal fields gets defaults
    assert state.inputs[1].name == "input_2"
    assert state.inputs[1].state == 0
    assert state.inputs[1].s0_counter == 0


def test_parse_device_state_empty() -> None:
    """An empty response yields default dataclasses."""
    state = _parse_device_state({})
    assert state.agent.model == ""
    assert state.global_measure.voltage is None
    assert state.outputs == []
    assert state.inputs == []


async def test_get_state_auth_error(hass, aioclient_mock) -> None:
    """HTTP 401 raises NetioAuthError."""
    aioclient_mock.get(API_URL, status=401)
    client = _make_client(hass)
    with pytest.raises(NetioAuthError):
        await client.get_state()


async def test_get_state_forbidden(hass, aioclient_mock) -> None:
    """HTTP 403 raises NetioApiError (JSON API read disabled)."""
    aioclient_mock.get(API_URL, status=403)
    client = _make_client(hass)
    with pytest.raises(NetioApiError, match="not enabled"):
        await client.get_state()


async def test_get_state_unexpected_status(hass, aioclient_mock) -> None:
    """Other HTTP errors raise NetioApiError with body text."""
    aioclient_mock.get(API_URL, status=418, text="teapot")
    client = _make_client(hass)
    with pytest.raises(NetioApiError, match="HTTP 418: teapot"):
        await client.get_state()


async def test_get_state_invalid_json(hass, aioclient_mock) -> None:
    """Broken JSON raises NetioApiError."""
    aioclient_mock.get(API_URL, text="not json at all")
    client = _make_client(hass)
    with pytest.raises(NetioApiError, match="Invalid JSON response"):
        await client.get_state()


async def test_get_state_non_dict_json(hass, aioclient_mock) -> None:
    """A JSON list response raises NetioApiError."""
    aioclient_mock.get(API_URL, json=[1, 2, 3])
    client = _make_client(hass)
    with pytest.raises(NetioApiError, match="Unexpected response type: list"):
        await client.get_state()


async def test_get_state_client_error(hass, aioclient_mock) -> None:
    """aiohttp client errors raise NetioConnectionError."""
    aioclient_mock.get(API_URL, exc=aiohttp.ClientError("boom"))
    client = _make_client(hass)
    with pytest.raises(NetioConnectionError, match="Cannot connect"):
        await client.get_state()


async def test_get_state_timeout(hass, aioclient_mock) -> None:
    """Timeouts raise NetioConnectionError."""
    aioclient_mock.get(API_URL, exc=asyncio.TimeoutError())
    client = _make_client(hass)
    with pytest.raises(NetioConnectionError, match="Timeout"):
        await client.get_state()


async def test_set_output_success(hass, aioclient_mock) -> None:
    """set_output posts the command and parses the returned state."""
    aioclient_mock.post(API_URL, json=FULL_RESPONSE)
    client = _make_client(hass)

    state = await client.set_output(1, 1)

    assert state.outputs[0].state == 1
    call = aioclient_mock.mock_calls[-1]
    assert call[0] == "POST"
    assert call[2] == {"Outputs": [{"ID": 1, "Action": 1}]}


async def test_set_outputs_success(hass, aioclient_mock) -> None:
    """set_outputs posts multiple commands at once."""
    aioclient_mock.post(API_URL, json=FULL_RESPONSE)
    client = _make_client(hass)

    commands = [{"ID": 1, "Action": 0}, {"ID": 2, "Action": 1, "Delay": 2000}]
    await client.set_outputs(commands)

    call = aioclient_mock.mock_calls[-1]
    assert call[2] == {"Outputs": commands}


@pytest.mark.parametrize(
    ("status", "match"),
    [
        (400, "Bad request"),
        (500, "internal error"),
        (418, "HTTP 418: teapot"),
    ],
)
async def test_post_http_errors(hass, aioclient_mock, status, match) -> None:
    """POST error statuses raise NetioApiError."""
    aioclient_mock.post(API_URL, status=status, text="teapot")
    client = _make_client(hass)
    with pytest.raises(NetioApiError, match=match):
        await client.set_output(1, 1)


async def test_post_auth_error(hass, aioclient_mock) -> None:
    """POST with HTTP 401 raises NetioAuthError."""
    aioclient_mock.post(API_URL, status=401)
    client = _make_client(hass)
    with pytest.raises(NetioAuthError):
        await client.set_output(1, 1)


async def test_post_forbidden(hass, aioclient_mock) -> None:
    """POST with HTTP 403 raises NetioApiError (write disabled)."""
    aioclient_mock.post(API_URL, status=403)
    client = _make_client(hass)
    with pytest.raises(NetioApiError, match="write is not enabled"):
        await client.set_output(1, 1)


async def test_post_invalid_json(hass, aioclient_mock) -> None:
    """POST with broken JSON body raises NetioApiError."""
    aioclient_mock.post(API_URL, text="garbage")
    client = _make_client(hass)
    with pytest.raises(NetioApiError, match="Invalid JSON response"):
        await client.set_output(1, 1)


async def test_post_non_dict_json(hass, aioclient_mock) -> None:
    """POST returning a JSON list raises NetioApiError."""
    aioclient_mock.post(API_URL, json=[])
    client = _make_client(hass)
    with pytest.raises(NetioApiError, match="Unexpected response type: list"):
        await client.set_output(1, 1)


async def test_post_result_error(hass, aioclient_mock) -> None:
    """POST returning an API error object raises NetioApiError."""
    aioclient_mock.post(
        API_URL,
        json={"result": {"error": {"code": 33, "message": "bad action"}}},
    )
    client = _make_client(hass)
    with pytest.raises(NetioApiError, match="API error 33: bad action"):
        await client.set_output(1, 7)


async def test_post_client_error(hass, aioclient_mock) -> None:
    """POST aiohttp client errors raise NetioConnectionError."""
    aioclient_mock.post(API_URL, exc=aiohttp.ClientError("down"))
    client = _make_client(hass)
    with pytest.raises(NetioConnectionError, match="Cannot connect"):
        await client.set_output(1, 1)


async def test_post_timeout(hass, aioclient_mock) -> None:
    """POST timeouts raise NetioConnectionError."""
    aioclient_mock.post(API_URL, exc=asyncio.TimeoutError())
    client = _make_client(hass)
    with pytest.raises(NetioConnectionError, match="Timeout"):
        await client.set_output(1, 1)


@pytest.mark.parametrize(
    ("base_url", "expected"),
    [
        ("http://192.168.1.10:80", "http://192.168.1.10"),
        ("https://192.168.1.10:443", "https://192.168.1.10"),
        ("http://192.168.1.10:8080", "http://192.168.1.10:8080"),
        ("http://192.168.1.10:8080/", "http://192.168.1.10:8080"),
        ("http://[fe80::1]:80", "http://[fe80::1]"),
        ("http://[fe80::1]:8080", "http://[fe80::1]:8080"),
    ],
)
async def test_web_url_variants(hass, base_url, expected) -> None:
    """web_url strips only standard ports and keeps IPv6 brackets."""
    client = _make_client(hass, base_url)
    assert client.web_url == expected
