# NETIO for Home Assistant

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![Validate](https://github.com/tuldener/ha-netio/actions/workflows/validate.yaml/badge.svg)](https://github.com/tuldener/ha-netio/actions/workflows/validate.yaml)
[![GitHub Release](https://img.shields.io/github/v/release/tuldener/ha-netio)](https://github.com/tuldener/ha-netio/releases)

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=tuldener&repository=ha-netio&category=integration)

Home Assistant custom integration for [NETIO](https://www.netio-products.com/) networked power sockets and PDUs.

Uses the **NETIO JSON over HTTP(s) M2M API** (Protocol Version 2.4) to read device status and control power outputs.

## Supported Devices

### Current Products

| Family | Models |
|--------|--------|
| PowerPDU | 4PS, 4KS, 4PV, 4KB, 4PB, 8QV, 8QS, 8KS, 8KF, 8QB, 8KB |
| PowerCable | 1Kx, 2KB, 2PZ, 2KZ, 2PB |
| PowerBOX | 3Px, 4Kx |
| PowerDIN | 4PZ, ZK3, ZP3 |
| 3-Phase | PowerPDU VK6, FK6 |

### Obsolete Products (still supported)

PowerPDU 4C, NETIO 4, NETIO 4All

> Source: [netio-products.com](https://www.netio-products.com/en/products/all-products) and [obsolete products](https://www.netio-products.com/en/products/obsolete-products)

### Energy Metering

Energy metering sensors are automatically created for devices that support it. Per NETIO documentation, metering is available on: PowerPDU 4C, PowerCable REST 101x, PowerBOX 4Kx, PowerDIN 4PZ, PowerPDU 8QS, and newer metered models (4KS, 8KS, 8KF, etc.).

The integration auto-detects metering support from the device's JSON API response.

## Prerequisites

1. Your NETIO device must be accessible on your network (LAN/WiFi).
2. The **JSON API** must be enabled on the device:
   - Open the device's web interface
   - Navigate to **M2M API Protocols** → **JSON API**
   - Enable **JSON API** and **READ** (and **WRITE** for control)
   - Note the port and credentials

## Installation

### HACS (recommended)

1. Open HACS in Home Assistant
2. Click the three dots → **Custom repositories**
3. Add `https://github.com/tuldener/ha-netio` as **Integration**
4. Search for "NETIO" and install
5. Restart Home Assistant

### Manual

1. Copy `custom_components/netio` to your `config/custom_components/netio` directory
2. Restart Home Assistant

## Configuration

1. Go to **Settings** → **Devices & Services** → **Add Integration**
2. Search for "NETIO"
3. Enter:
   - **Host**: IP address or hostname of your NETIO device
   - **Port**: HTTP port (default: 80, check device web config)
   - **Username**: JSON API username (default: `netio`)
   - **Password**: JSON API password (default: `netio` for standard devices)
   - **Use HTTPS**: Check if your device uses HTTPS (PowerPDU 4C only)

## Entities

### Switches

One switch entity per power output. Supports on/off control.

Entity ID format: `switch.{device_name}_{output_name}`

### Sensors (metered devices only)

Per-output sensors:
- Current (mA)
- Load / Power (W)
- Energy (Wh) — total increasing
- Power Factor
- Reverse Energy (Wh) — where available

Global sensors:
- Voltage (V)
- Frequency (Hz)
- Total Current (mA)
- Total Load (W)
- Total Energy (Wh)
- Total Power Factor

### Binary Sensors (devices with digital inputs)

One binary sensor per digital input (e.g. PowerDIN 4PZ).

Plus an S0 pulse counter sensor per input.

## Protocol Details

This integration uses the **JSON over HTTP(s)** protocol exclusively:

- **Read**: `GET http://<device>/netio.json`
- **Write**: `POST http://<device>/netio.json` with JSON body
- **Authentication**: HTTP Basic Auth
- **Polling interval**: 30 seconds

For protocol details, see the [NETIO JSON API documentation](https://www.netio-products.com/en/software/open-api).

## License

MIT
