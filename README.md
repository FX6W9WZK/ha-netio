# NETIO for Home Assistant

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![Validate](https://github.com/FX6W9WZK/ha-netio/actions/workflows/validate.yaml/badge.svg)](https://github.com/FX6W9WZK/ha-netio/actions/workflows/validate.yaml)
[![GitHub Release](https://img.shields.io/github/v/release/FX6W9WZK/ha-netio)](https://github.com/FX6W9WZK/ha-netio/releases)
[![Built with Claude AI](https://img.shields.io/badge/Built_with-Claude_AI-D4A27F?logo=anthropic&logoColor=white)](https://www.anthropic.com/claude)

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=FX6W9WZK&repository=ha-netio&category=integration)

Home Assistant custom integration for [NETIO](https://www.netio-products.com/) networked power sockets and PDUs.

Uses the **NETIO JSON over HTTP(s) M2M API** (Protocol Version 2.4) to read device status and control power outputs.

![NETIO Device Card](docs/card-preview.png)

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

**Tested Devices:** PowerPDU 4C

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
3. Add `https://github.com/FX6W9WZK/ha-netio` as **Integration**
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

### Buttons

Per-output action buttons (per NETIO JSON API specification):
- **Restart** (Short OFF) — Action 2: Switches output OFF for a defined time, then back ON. Protected during delay.
- **Short ON** — Action 3: Switches output ON for a defined time, then back OFF.
- **Toggle** — Action 4: Inverts the current output state.

### Binary Sensors (devices with digital inputs)

One binary sensor per digital input (e.g. PowerDIN 4PZ).

Plus an S0 pulse counter sensor per input.

## Lovelace Cards

The integration includes three custom Lovelace cards with glassmorphism design, inspired by [Bubble Card](https://github.com/Clooos/Bubble-Card).

| Card | Description |
|------|-------------|
| `netio-card` | All NETIO outlets across **all** devices |
| `netio-device-card` | All outlets of **one** specific NETIO device |
| `netio-outlet-card` | **Single** outlet |

### Installation

Add the card as a Lovelace resource:

**Settings** → **Dashboards** → **Resources** → **Add Resource**

| URL | Type |
|---|---|
| `/netio/netio-card.js` | JavaScript Module |

The resource is automatically registered when the integration loads.

### Usage

```yaml
type: custom:netio-card
title: NETIO
show_energy: true
show_actions: true
theme: auto
accent_color: ""
```

### Card Features

- Auto-discovers all NETIO outlet entities
- Accordion layout — one output expanded at a time
- ON/OFF toggle, Restart, Short ON, Toggle buttons
- Energy metering display (W, mA, Wh, Power Factor)
- Global device info (Voltage, Frequency, Total Load)
- Dark / Light mode (automatic or manual)
- Customizable accent color (default: NETIO green)
- Visual card editor in Lovelace UI
- Multilingual (German / English)

## Protocol Details

This integration uses the **JSON over HTTP(s)** protocol exclusively:

- **Read**: `GET http://<device>/netio.json`
- **Write**: `POST http://<device>/netio.json` with JSON body
- **Authentication**: HTTP Basic Auth
- **Polling interval**: 30 seconds

For protocol details, see the [NETIO JSON API documentation](https://www.netio-products.com/en/software/open-api).

## MQTT-flex (Alternative: HA native MQTT)

If you prefer push-based updates instead of polling, you can use NETIO's **MQTT-flex** protocol with Home Assistant's built-in MQTT integration. This does not require `ha-netio` — it uses HA's native MQTT support.

> **Supported devices for MQTT-flex** (per [NETIO Wiki](https://wiki.netio-products.com/index.php?title=MQTT-flex)):
> PowerCable MQTT 101x, PowerCable REST 101x, PowerPDU 4PS, PowerPDU 4KS,
> PowerPDU 8QS, PowerDIN 4PZ, PowerBOX 3Px, PowerBOX 4Kx (FW ≥ 2.2.1)
>
> **Not supported:** PowerPDU 4C, NETIO 4, NETIO 4All (these use the older fixed MQTT, not MQTT-flex)

### Step 1: MQTT-flex Config for the NETIO Device

Paste the following JSON into your NETIO device under **M2M API Protocols → MQTT-flex**. Replace the broker credentials with your own (e.g. your Home Assistant Mosquitto broker).

**Single-output device** (PowerCable 1Kx):

```json
{
  "config": {
    "broker": {
      "url": "YOUR_HA_IP",
      "protocol": "mqtt",
      "port": 1883,
      "ssl": false,
      "type": "generic",
      "username": "mqtt_user",
      "password": "mqtt_password",
      "clientid": "netio_${DEVICE_NAME}"
    },
    "subscribe": [
      {
        "topic": "netio/${DEVICE_NAME}/output/1/action",
        "qos": 0,
        "target": "OUTPUTS/1/ACTION",
        "action": "${payload}"
      }
    ],
    "publish": [
      {
        "topic": "netio/${DEVICE_NAME}/output/1/state",
        "qos": 0, "retain": true,
        "payload": "${OUTPUTS/1/STATE}",
        "events": [{ "type": "change", "source": "OUTPUTS/1/STATE" }]
      },
      {
        "topic": "netio/${DEVICE_NAME}/output/1/load",
        "qos": 0, "retain": false,
        "payload": "${OUTPUTS/1/LOAD}",
        "events": [
          { "type": "timer", "period": 60 },
          { "type": "delta", "source": "OUTPUTS/1/LOAD", "delta": 1 }
        ]
      },
      {
        "topic": "netio/${DEVICE_NAME}/output/1/current",
        "qos": 0, "retain": false,
        "payload": "${OUTPUTS/1/CURRENT}",
        "events": [
          { "type": "timer", "period": 60 },
          { "type": "delta", "source": "OUTPUTS/1/CURRENT", "delta": 10 }
        ]
      },
      {
        "topic": "netio/${DEVICE_NAME}/output/1/energy",
        "qos": 0, "retain": false,
        "payload": "${OUTPUTS/1/ENERGY}",
        "events": [{ "type": "timer", "period": 300 }]
      },
      {
        "topic": "netio/${DEVICE_NAME}/output/1/voltage",
        "qos": 0, "retain": false,
        "payload": "${OUTPUTS/1/VOLTAGE}",
        "events": [{ "type": "timer", "period": 60 }]
      },
      {
        "topic": "netio/${DEVICE_NAME}/output/1/frequency",
        "qos": 0, "retain": false,
        "payload": "${OUTPUTS/1/FREQUENCY}",
        "events": [{ "type": "timer", "period": 60 }]
      }
    ]
  }
}
```

**Multi-output device** (PowerBOX 4Kx, PowerPDU 4KS, etc.): Duplicate the subscribe and publish entries for each output (replace `/1/` with `/2/`, `/3/`, `/4/` etc.). For global totals, use `OUTPUTS/TOTAL/LOAD`, `OUTPUTS/TOTAL/ENERGY`, etc.

### Step 2: Home Assistant MQTT Configuration

Add to your `configuration.yaml`:

```yaml
mqtt:
  switch:
    - name: "NETIO Output 1"
      state_topic: "netio/MyNetio/output/1/state"
      command_topic: "netio/MyNetio/output/1/action"
      payload_on: "1"
      payload_off: "0"
      state_on: "1"
      state_off: "0"
      device_class: outlet

  sensor:
    - name: "NETIO Output 1 Load"
      state_topic: "netio/MyNetio/output/1/load"
      unit_of_measurement: "W"
      device_class: power
      state_class: measurement

    - name: "NETIO Output 1 Current"
      state_topic: "netio/MyNetio/output/1/current"
      unit_of_measurement: "mA"
      device_class: current
      state_class: measurement

    - name: "NETIO Output 1 Energy"
      state_topic: "netio/MyNetio/output/1/energy"
      unit_of_measurement: "Wh"
      device_class: energy
      state_class: total_increasing

    - name: "NETIO Voltage"
      state_topic: "netio/MyNetio/output/1/voltage"
      unit_of_measurement: "V"
      device_class: voltage
      state_class: measurement

    - name: "NETIO Frequency"
      state_topic: "netio/MyNetio/output/1/frequency"
      unit_of_measurement: "Hz"
      device_class: frequency
      state_class: measurement
```

Replace `MyNetio` with your NETIO device name (shown in the device web interface under Settings → System → Device name).

### Additional MQTT Actions

To restart an output (short OFF) or send a short ON pulse via MQTT, publish the action value to the command topic:

| Action | Payload | Description |
|--------|---------|-------------|
| OFF | `0` | Turn output off |
| ON | `1` | Turn output on |
| Short OFF | `2` | Restart (off for delay, then on) |
| Short ON | `3` | On for delay, then off |
| Toggle | `4` | Invert current state |

Example automation:

```yaml
# Restart Output 1 via MQTT
action:
  - action: mqtt.publish
    data:
      topic: "netio/MyNetio/output/1/action"
      payload: "2"
```

### When to Use MQTT-flex vs. ha-netio

| Aspect | ha-netio (JSON API) | MQTT-flex (native HA MQTT) |
|--------|--------------------|-----------------------------|
| Setup | Config flow UI | Manual YAML + device config |
| Updates | Polling (30s) | Push (instant state changes) |
| Energy data | Auto-detected | Manual per-sensor YAML |
| Buttons (Restart etc.) | Built-in entities | Service calls / automations |
| Dashboard card | Included | Standard HA cards |
| Requires broker | No | Yes (Mosquitto etc.) |
| Device auto-discovery | Yes | No |

Both approaches can coexist — you can use ha-netio for the main integration and additionally subscribe to MQTT topics for faster state updates.

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for the full version history.
