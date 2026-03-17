"""NETIO API client for JSON over HTTP(s) protocol.

Based on NETIO M2M API Protocol documentation:
- JSON Version 2.4 (20.07.2021)
- Read: HTTP(s) GET to /netio.json
- Write: HTTP(s) POST to /netio.json with JSON body
- Auth: HTTP Basic Authentication

Supported devices per documentation:
  Linux-based: PowerPDU 4C (obsolete), NETIO 4/4All (obsolete)
  Standard: PowerCable REST 101x, PowerBOX 3Px, PowerBOX 4Kx,
            PowerDIN 4KZ, PowerPDU 4PS, PowerPDU 8QS
  (Newer devices like 4KS, 8KS, 8KF etc. also use JSON API)
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any

import aiohttp

from .const import (
    ACTION_IGNORED,
    ACTION_OFF,
    ACTION_ON,
    ACTION_TOGGLE,
    NETIO_JSON_ENDPOINT,
)

_LOGGER = logging.getLogger(__name__)


class NetioApiError(Exception):
    """Base exception for NETIO API errors."""


class NetioAuthError(NetioApiError):
    """Authentication error (HTTP 401)."""


class NetioConnectionError(NetioApiError):
    """Connection error."""


@dataclass
class NetioOutput:
    """Represents a single NETIO power output."""

    id: int
    name: str
    state: int  # 0=OFF, 1=ON
    action: int  # 6=ignored in read responses
    delay: int  # ms, short on/off delay
    # Energy metering (optional, not all devices support this)
    current: int | None = None  # mA
    power_factor: float | None = None
    phase: float | None = None  # degrees
    load: int | None = None  # W
    energy: int | None = None  # Wh
    energy_nr: int | None = None  # Wh, not resettable
    reverse_energy: int | None = None  # Wh
    reverse_energy_nr: int | None = None  # Wh, not resettable


@dataclass
class NetioInput:
    """Represents a single NETIO digital input."""

    id: int
    name: str
    state: int  # 0=open/ON, 1=closed/OFF
    s0_counter: int


@dataclass
class NetioGlobalMeasure:
    """Global electrical measurements for the entire device."""

    voltage: float | None = None  # V
    frequency: float | None = None  # Hz
    total_current: int | None = None  # mA
    overall_power_factor: float | None = None
    total_power_factor: float | None = None
    phase: float | None = None  # degrees
    total_phase: float | None = None
    total_load: int | None = None  # W
    total_energy: int | None = None  # Wh
    total_energy_nr: int | None = None  # Wh
    total_reverse_energy: int | None = None  # Wh
    total_reverse_energy_nr: int | None = None  # Wh
    energy_start: str | None = None


@dataclass
class NetioAgent:
    """Device agent information."""

    model: str = ""
    version: str = ""
    json_ver: str = ""
    device_name: str = ""
    vendor_id: int = 0
    oem_id: int = 0
    mac: str = ""
    serial_number: str = ""
    uptime: int = 0
    time: str = ""
    num_outputs: int = 0
    num_inputs: int = 0


@dataclass
class NetioDeviceState:
    """Complete device state from a single JSON API read."""

    agent: NetioAgent = field(default_factory=NetioAgent)
    global_measure: NetioGlobalMeasure = field(default_factory=NetioGlobalMeasure)
    outputs: list[NetioOutput] = field(default_factory=list)
    inputs: list[NetioInput] = field(default_factory=list)


def _parse_output(data: dict[str, Any]) -> NetioOutput:
    """Parse a single output from JSON response."""
    return NetioOutput(
        id=data["ID"],
        name=data.get("Name", f"output_{data['ID']}"),
        state=data.get("State", 0),
        action=data.get("Action", ACTION_IGNORED),
        delay=data.get("Delay", 5000),
        current=data.get("Current"),
        power_factor=data.get("PowerFactor"),
        phase=data.get("Phase"),
        load=data.get("Load"),
        energy=data.get("Energy"),
        energy_nr=data.get("EnergyNR"),
        reverse_energy=data.get("ReverseEnergy"),
        reverse_energy_nr=data.get("ReverseEnergyNR"),
    )


def _parse_input(data: dict[str, Any]) -> NetioInput:
    """Parse a single input from JSON response."""
    return NetioInput(
        id=data["ID"],
        name=data.get("Name", f"input_{data['ID']}"),
        state=data.get("State", 0),
        s0_counter=data.get("S0Counter", 0),
    )


def _parse_agent(data: dict[str, Any]) -> NetioAgent:
    """Parse agent info from JSON response."""
    return NetioAgent(
        model=data.get("Model", ""),
        version=data.get("Version", ""),
        json_ver=data.get("JSONVer", ""),
        device_name=data.get("DeviceName", ""),
        vendor_id=data.get("VendorID", 0),
        oem_id=data.get("OemID", 0),
        mac=data.get("MAC", ""),
        serial_number=data.get("SerialNumber", ""),
        uptime=data.get("Uptime", 0),
        time=data.get("Time", ""),
        num_outputs=data.get("NumOutputs", 0),
        num_inputs=data.get("NumInputs", 0),
    )


def _parse_global_measure(data: dict[str, Any]) -> NetioGlobalMeasure:
    """Parse global measurements from JSON response."""
    return NetioGlobalMeasure(
        voltage=data.get("Voltage"),
        frequency=data.get("Frequency"),
        total_current=data.get("TotalCurrent"),
        overall_power_factor=data.get("OverallPowerFactor"),
        total_power_factor=data.get("TotalPowerFactor"),
        phase=data.get("Phase"),
        total_phase=data.get("TotalPhase"),
        total_load=data.get("TotalLoad"),
        total_energy=data.get("TotalEnergy"),
        total_energy_nr=data.get("TotalEnergyNR"),
        total_reverse_energy=data.get("TotalReverseEnergy"),
        total_reverse_energy_nr=data.get("TotalReverseEnergyNR"),
        energy_start=data.get("EnergyStart"),
    )


def _parse_device_state(data: dict[str, Any]) -> NetioDeviceState:
    """Parse full device state from JSON API response."""
    state = NetioDeviceState()

    if "Agent" in data:
        state.agent = _parse_agent(data["Agent"])

    if "GlobalMeasure" in data:
        state.global_measure = _parse_global_measure(data["GlobalMeasure"])

    if "Outputs" in data:
        state.outputs = [_parse_output(o) for o in data["Outputs"]]

    if "Inputs" in data:
        state.inputs = [_parse_input(i) for i in data["Inputs"]]

    return state


class NetioApiClient:
    """Client for NETIO JSON over HTTP(s) API.

    Per NETIO documentation:
    - GET /netio.json returns device status (read)
    - POST /netio.json with JSON body controls outputs (write)
    - Basic HTTP authentication
    - Default credentials: netio/netio (standard devices)
      or netio/<MAC-without-colons> for PowerPDU 4C (write)
    """

    def __init__(
        self,
        base_url: str,
        username: str,
        password: str,
        session: aiohttp.ClientSession | None = None,
        verify_ssl: bool = True,
    ) -> None:
        """Initialize the API client.

        Args:
            base_url: Device base URL, e.g. "http://192.168.1.100" or
                      "http://192.168.1.100:8080"
            username: JSON API username
            password: JSON API password
            session: Optional aiohttp session (created if not provided)
            verify_ssl: Whether to verify SSL certificates
        """
        self._base_url = base_url.rstrip("/")
        self._auth = aiohttp.BasicAuth(username, password)
        self._session = session
        self._owns_session = session is None
        self._verify_ssl = verify_ssl
        self._url = f"{self._base_url}{NETIO_JSON_ENDPOINT}"
        # Web admin URL (without API port)
        from urllib.parse import urlparse
        parsed = urlparse(self._base_url)
        self.web_url = f"{parsed.scheme}://{parsed.hostname}"

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create the aiohttp session."""
        if self._session is None or self._session.closed:
            connector = aiohttp.TCPConnector(ssl=self._verify_ssl)
            self._session = aiohttp.ClientSession(connector=connector)
            self._owns_session = True
        return self._session

    async def close(self) -> None:
        """Close the session if we own it."""
        if self._owns_session and self._session and not self._session.closed:
            await self._session.close()

    async def get_state(self) -> NetioDeviceState:
        """Read device state via HTTP GET.

        Returns full device state including agent info, measurements,
        output states, and input states (where available).

        Raises:
            NetioAuthError: Invalid credentials (HTTP 401)
            NetioConnectionError: Cannot reach device
            NetioApiError: Other API errors
        """
        session = await self._get_session()
        try:
            async with session.get(
                self._url,
                auth=self._auth,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                if resp.status == 401:
                    raise NetioAuthError("Invalid username or password")
                if resp.status == 403:
                    raise NetioApiError("JSON API read is not enabled on device")
                if resp.status != 200:
                    text = await resp.text()
                    raise NetioApiError(
                        f"HTTP {resp.status}: {text}"
                    )
                try:
                    data = await resp.json(content_type=None)
                except (ValueError, Exception) as err:
                    text = await resp.text()
                    raise NetioApiError(
                        f"Invalid JSON response: {err} (body: {text[:200]})"
                    ) from err

                if not isinstance(data, dict):
                    raise NetioApiError(
                        f"Unexpected response type: {type(data).__name__}"
                    )
                return _parse_device_state(data)

        except aiohttp.ClientError as err:
            raise NetioConnectionError(
                f"Cannot connect to {self._base_url}: {err}"
            ) from err
        except asyncio.TimeoutError as err:
            raise NetioConnectionError(
                f"Timeout connecting to {self._base_url}"
            ) from err

    async def set_output(self, output_id: int, action: int) -> NetioDeviceState:
        """Control a single output.

        Per JSON API documentation:
        - Action values: 0=off, 1=on, 2=short off, 3=short on,
                         4=toggle, 5=no change, 6=ignored
        - POST body: {"Outputs": [{"ID": <X>, "Action": <Z>}]}
        - On success, returns updated device state (HTTP 200)

        Args:
            output_id: Output number (1-based)
            action: Action value (0-6)

        Returns:
            Updated device state

        Raises:
            NetioAuthError: Invalid credentials
            NetioConnectionError: Cannot reach device
            NetioApiError: Other API errors
        """
        payload = {"Outputs": [{"ID": output_id, "Action": action}]}
        return await self._post(payload)

    async def set_outputs(
        self, commands: list[dict[str, int]]
    ) -> NetioDeviceState:
        """Control multiple outputs at once.

        Args:
            commands: List of dicts with "ID" and "Action" keys,
                      optionally "Delay" (ms) for short on/off actions.

        Returns:
            Updated device state
        """
        payload = {"Outputs": commands}
        return await self._post(payload)

    async def _post(self, payload: dict[str, Any]) -> NetioDeviceState:
        """Send a POST command to the device.

        Per documentation, a successful POST returns HTTP 200 and
        the current device state as JSON.
        """
        session = await self._get_session()
        try:
            async with session.post(
                self._url,
                json=payload,
                auth=self._auth,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                if resp.status == 401:
                    raise NetioAuthError("Invalid username or password")
                if resp.status == 403:
                    raise NetioApiError(
                        "JSON API write is not enabled on device"
                    )
                if resp.status == 400:
                    raise NetioApiError("Bad request - command syntax error")
                if resp.status == 500:
                    raise NetioApiError(
                        "Device internal error (may be restarting)"
                    )
                if resp.status != 200:
                    text = await resp.text()
                    raise NetioApiError(f"HTTP {resp.status}: {text}")

                try:
                    data = await resp.json(content_type=None)
                except (ValueError, Exception) as err:
                    text = await resp.text()
                    raise NetioApiError(
                        f"Invalid JSON response: {err} (body: {text[:200]})"
                    ) from err

                if not isinstance(data, dict):
                    raise NetioApiError(
                        f"Unexpected response type: {type(data).__name__}"
                    )

                # Per documentation, error responses have a "result" key
                if "result" in data and "error" in data["result"]:
                    err = data["result"]["error"]
                    raise NetioApiError(
                        f"API error {err.get('code')}: {err.get('message')}"
                    )

                return _parse_device_state(data)

        except aiohttp.ClientError as err:
            raise NetioConnectionError(
                f"Cannot connect to {self._base_url}: {err}"
            ) from err
        except asyncio.TimeoutError as err:
            raise NetioConnectionError(
                f"Timeout connecting to {self._base_url}"
            ) from err
