# Changelog

All notable changes to this project are documented here.

### v1.0.0 (2025-03-15)

**First stable release.**

#### Features
- **3 Lovelace cards**: Combined (`netio-card`), per-device (`netio-device-card`), single outlet (`netio-outlet-card`)
- **Toggle switch** with green/red status indication
- **`mdi:power-socket-eu` default icon**, customisable via HA icon picker
- **NETIO logo** in card header
- **Labels & icons per outlet** in visual card editor
- **Clean outlet names** — hostname prefix stripped automatically
- **Outlets sorted alphabetically** by displayed name
- **Static card picker previews** for Device and Outlet cards
- **Action buttons** (Restart, Short ON, Toggle) at 50% width, conditional display
- **Energy metering** (W, mA, Wh, Power Factor) and global sensors (V, Hz, total load)
- **Options flow** — enable/disable action buttons per device
- **Reconfigure flow** — change connection settings without removing
- **Dynamic name sync** — socket names update automatically from NETIO device (every 30s, only on change)
- **Parent device always created** — correct device hierarchy for sub-devices
- **DHCP discovery** — auto-detect NETIO devices on the network (MAC prefix 24:A4:2C)
- **Multi-device support** — multiple NETIO devices on one HA instance

#### Supported devices
PowerPDU (4PS, 4KS, 4PV, 4KB, 4PB, 8QV, 8QS, 8KS, 8KF, 8QB, 8KB), PowerCable (1Kx, 2KB, 2PZ, 2KZ, 2PB), PowerBOX (3Px, 4Kx), PowerDIN (4PZ, ZK3, ZP3), 3-Phase (VK6, FK6), PowerPDU 4C, NETIO 4, NETIO 4All

**Tested:** PowerPDU 4C

### v0.9.9 (2025-03-15)

**Changed**
- **GitHub username changed** — All references updated from `tuldener` to `FX6W9WZK`: manifest.json (codeowners, documentation, issue_tracker), README badges and links, HACS install link, Lovelace card documentationURL.

### v0.9.8 (2025-03-15)

**Fixed**
- **Editor dropdowns show saved selection** — The Device and Outlet card editors now correctly show the previously selected device/entity when reopened. Fixed a race condition where `set hass()` could arrive before `setConfig()`, causing the dropdown to render with empty config and never update. The editor now re-renders when the key selection (entity or device_id) changes, but NOT when labels/icons/title change (preserving text editing).

### v0.9.7 (2025-03-15)

**Fixed**
- **Parent device name not updating** — The `_update_device_names` method used `self.device_serial` which depends on `self.data`. During the first poll, `self.data` is still `None` (set by the framework AFTER `_async_update_data` returns), so the serial fell back to the config entry ID — the device was never found in the registry. Now computes the serial directly from the polled state.

### v0.9.6 (2025-03-15)

**Added**
- **Dynamic name sync from NETIO device** — The coordinator now tracks the device hostname and all output socket names from the JSON API. After each poll (every 30s), if a name changed on the NETIO device (e.g. via its web admin), the HA device registry is updated automatically. Only writes to the registry when a name actually differs — no unnecessary updates.

### v0.9.5 (2025-03-15)

**Changed**
- **Outlets sorted by displayed name** — The combined card (`netio-card`) and device card (`netio-device-card`) now sort outlets alphabetically by their resolved display name (label > socket name > entity_id).

### v0.9.4 (2025-03-15)

**Fixed**
- **Multiple NETIO devices crash on startup** — When two or more NETIO integrations were configured, the second entry crashed with `RuntimeError: Added route will never be executed, method GET is already registered`. The static card route `/netio/netio-card.js` only needs to be registered once — the `RuntimeError` from duplicate registration is now caught silently.

### v0.9.3 (2025-03-15)

**Changed**
- **Action buttons 50% width** — ON/OFF, Toggle, Restart, Short ON buttons now each take 50% of the row width (2 per row). With all 3 action buttons enabled (4 buttons total), they wrap into 2 rows of 2.

### v0.9.2 (2025-03-15)

**Changed**
- **Static preview in card picker** — When adding a new card via the dashboard picker, the Device and Outlet cards now show a realistic mock layout (with sample outlets, toggle switches, and the NETIO header) instead of the "Kein Gerät/Ausgang ausgewählt" empty state. This makes it easy to see what the card looks like before configuring it.

### v0.9.1 (2025-03-15)

**Changed**
- **Default card titles adjusted:**
  - `netio-card` (combined): Default title remains **"NETIO"**
  - `netio-device-card`: Default title is now the **device name** (e.g. "stjane01") instead of "NETIO"
  - `netio-outlet-card`: Default title is the **outlet name without device prefix** (e.g. "Kabine01" instead of "stjane01 Kabine01") — unchanged, already worked this way since v0.8.3

### v0.9.0 (2025-03-15)

**Compliance review — HA & HACS standards verified**

All files reviewed against Home Assistant and HACS requirements:

- `manifest.json`: domain, name, version, documentation, issue_tracker, codeowners, iot_class, config_flow, dhcp, after_dependencies — all present and correct. Removed empty `requirements: []`.
- `config_flow.py`: ConfigFlow, OptionsFlow, and Reconfigure flow all implemented.
- `strings.json` ↔ `translations/en.json` ↔ `translations/de.json`: all keys in sync.
- `hacs.json`: name and render_readme set.
- `LICENSE`: present.
- `.github/workflows/validate.yaml`: HACS and hassfest validation on push/PR/daily.

**Fixed**
- **Button entities now have `EntityCategory.CONFIG`** — Restart, Short ON, and Toggle buttons are correctly categorized as configuration entities per HA best practices.
- **Removed empty `requirements` from manifest.json** — hassfest recommends omitting the key entirely if empty.

**Verified (no changes needed)**
- Sensor device classes (`SensorDeviceClass`) and state classes (`SensorStateClass`) correctly set on all sensors.
- Switch device class: `SwitchDeviceClass.OUTLET`.
- `_attr_has_entity_name = True` on all entity base classes.
- `DataUpdateCoordinator` with `async_config_entry_first_refresh`.
- `runtime_data` pattern (modern, no `hass.data[DOMAIN]`).
- No blocking I/O in event loop — all network via `aiohttp`.
- Proper `async_setup_entry` / `async_unload_entry` in `__init__.py`.
- All 4 platforms: switch, sensor, binary_sensor, button.
- 3 Lovelace cards: netio-card, netio-device-card, netio-outlet-card (6 custom elements total).
- Card JS syntax valid, 3 cards registered with `window.customCards`.
- icon.png and logo.png present.

### v0.8.5 (2025-03-15)

**Changed**
- **README: Tested devices** — Added PowerPDU 4PS as tested device under Current Products.
- **README: Built with Claude AI badge** — Added transparent shield badge linking to Anthropic Claude.

### v0.8.4 (2025-03-15)

**Changed**
- **README updated** — Card preview screenshot added, Lovelace section rewritten with three-card overview table.

### v0.8.3 (2025-03-15)

**Changed**
- **Default icon is now `mdi:power-socket-eu`** — All three cards use the HA power socket icon instead of the built-in SVG plug icon. Custom icons via the icon picker still override this default.
- **Output names show only the NETIO socket name** — Names like "stjane01 Kabine01" are now displayed as just "Kabine01". The hostname prefix is stripped by looking up the parent device name in the HA device registry. Falls back to stripping the first word for orphan devices. Custom labels still take priority.

### v0.8.2 (2025-03-15)

**Fixed**
- **Parent device always created** — The parent device is now explicitly registered in the device registry (via `dev_reg.async_get_or_create()`) BEFORE platform entities are set up. This ensures that sub-device outlets always have a valid `via_device_id` pointing to their parent, even if the parent has no dedicated entities (global sensors).
- **Device card default title is now "NETIO"** — Previously defaulted to the HA device name (e.g. "stjane02 Kabine05").

### v0.8.1 (2025-03-15)

**Fixed**
- **Device card showed sub-devices instead of parent devices** — When a NETIO device has no parent entry in the device registry (orphan sub-devices with `via_device_id: null`), `nParentDevices` now groups them by serial number prefix from the device identifiers (e.g. `24:A4:2C:39:04:9A_output_1` → serial `24:A4:2C:39:04:9A`).
- **Unavailable entities no longer shown** — All three cards and their editors now filter out entities with state `unavailable`. This prevents unnamed "Switch" entries from offline devices appearing in the UI.
- **Entities named just "Switch" show entity_id instead** — The editor dropdowns now display the entity_id when the friendly_name is just "Switch" (no device prefix).

### v0.8.0 (2025-03-15)

**Added**
- **New card: `netio-device-card`** — Shows all outlets of a single NETIO master device. Select a device from the dropdown in the editor — the card auto-discovers all child outlets. Includes device model in subtitle, global sensors (voltage, frequency, total load), custom labels and icons per outlet. Ideal when you have multiple NETIO devices and want one card per device.

**Config example**
```yaml
type: custom:netio-device-card
device_id: 244c3aad52b1a5d182b6e2e03b8b385a
show_energy: true
```

**Card overview**
| Card | Description |
|------|-------------|
| `netio-card` | All NETIO outlets across all devices |
| `netio-device-card` | All outlets of one specific NETIO device |
| `netio-outlet-card` | Single outlet |

### v0.7.6 (2025-03-15)

**Fixed**
- **Device "Besuchen" link now updates on reload** — HA caches the `configuration_url` in the device registry and does not update it from `DeviceInfo` on subsequent loads. The integration now explicitly updates the device registry entry after platform setup, forcing the URL to the correct value (without API port).

### v0.7.5 (2025-03-15)

**Fixed**
- **Device info link no longer includes API port** — The configuration URL in the device info page now points to `http(s)://host` (web admin) instead of `http(s)://host:port` (API endpoint).

### v0.7.4 (2025-03-15)

**Fixed**
- **Switch could not be turned back on after turning off** — The click handler in `_attachEvt` captured the `hass` object at render time. After a state change, HA provides a new `hass` object via `set hass()`, but the old click handler still read the stale state (always saw "on"), so it always called `turn_off`. Now `_attachEvt` receives the card instance and reads `card._hass` at click time, always getting the current state.

### v0.7.3 (2025-03-15)

**Fixed**
- **Labels and icons could not be saved in combined card editor** — HA freezes the config object passed to `setConfig()`. The editor tried to mutate it directly (`this._config.labels[entity] = value`), causing `TypeError: Cannot assign to read only property`. All event handlers now create new object copies via spread operator before dispatching `config-changed`.

### v0.7.2 (2025-03-15)

**Fixed**
- **NETIO logo centered in header icon** — The NETIO wordmark is now properly centered (vertically and horizontally) within the green header icon box.

### v0.7.1 (2025-03-15)

**Fixed**
- **Labels could not be edited/saved in combined card** — `setConfig()` was called by HA after every `config-changed` event, triggering a full DOM re-render that destroyed the editor form. Added `_didRender` guard to both editors.

**Changed**
- **Icon picker with search and preview** — Replaced the MDI text input with HA's native `<ha-icon-picker>` element. Click the icon field to open a searchable dropdown with visual icon previews. Works in both card editors.

### v0.7.0 (2025-03-15)

**Added**
- **Custom icons per output** — Both cards support custom MDI icons (e.g. `mdi:television`, `mdi:server`, `mdi:lamp`). In the combined card, each output has its own icon field next to the label. In the outlet card, a single icon field in the editor.
- **NETIO logo in card header** — The plug icon next to the title is replaced by the NETIO wordmark logo.

**Config example**
```yaml
# Combined card with custom icons
type: custom:netio-card
icons:
  switch.stjane01_kabine01: mdi:television
  switch.stjane01_kabine02: mdi:server-network

# Outlet card with custom icon
type: custom:netio-outlet-card
entity: switch.stjane01_kabine01
icon: mdi:television
```

### v0.6.6 (2025-03-15)

**Fixed**
- **"tg is not defined" error in cards** — The toggle switch refactoring left a variable name mismatch in `_updateExisting` and `_updateOutlet` (`const bd=...` but referenced as `tg`). Both now correctly use `tg`.

### v0.6.5 (2025-03-15)

**Changed**
- **Toggle switch replaces status badge** — The "Ein"/"Aus" text badge is replaced by a round iOS-style toggle switch (green = on, red = off). Clicking the toggle switches the outlet on/off.
- **Chevron/dropdown hidden when no actions** — The expand arrow is only shown if at least one of the three button entities (Restart, Short ON, Toggle) is enabled. If all are disabled, the output row has no dropdown.
- **Click-to-expand guarded** — Clicking the row only expands if there are action buttons to show.

### v0.6.4 (2025-03-15)

**Fixed**
- **Cards and editors constantly re-rendering** — `set hass()` triggered a full `innerHTML` rebuild on every HA state update (every few seconds), making text editing in the card editor impossible. Now:
  - Main card: incremental DOM updates via `_updateExisting()` (already existed)
  - Outlet card: new `_updateOutlet()` for incremental updates, full render only on first load or config change
  - Both editors: render only once when `hass` is first provided, not on every update

### v0.6.3 (2025-03-15)

**Fixed**
- **Card editor crash: "Cannot read properties of null (reading 'addEventListener')"** — The sed-based refactoring in v0.5.2/v0.6.0 accidentally removed the `innerHTML` template from both card editors. The editors tried to bind event listeners to non-existent DOM elements. Restored complete editor HTML templates.

### v0.6.2 (2025-03-15)

**Added**
- **Button options during initial setup** — When adding a new NETIO device, a second step now asks which button entities (Restart, Short ON, Toggle) should be enabled. This applies to both manual setup and DHCP discovery.

### v0.6.1 (2025-03-15)

**Added**
- **Reconfigure connection settings** — Host, Port, Username, Password and HTTPS can now be changed after initial setup via ⋮ Menu → "Reconfigure" on the integration page.

### v0.6.0 (2025-03-15)

**Added**
- **Options flow for button entity visibility** — Under Settings → Devices → NETIO device → "Configure", three toggles control which button entities are enabled (Restart, Short ON, Toggle). Disabled entities disappear from `hass.states` and are automatically hidden in Lovelace cards.

**Changed**
- Button visibility checkboxes removed from Lovelace card editors — now controlled centrally at device level.

### v0.5.2 (2025-03-15)

**Fixed**
- **Dashboard refresh loop** — Removed `ll-rebuild` event dispatch that forced Lovelace to rebuild on every card load, interrupting user interaction.

### v0.5.1 (2025-03-15)

**Added**
- **Editable output labels** — Both cards support custom names for outputs. Combined card: per-output labels in editor. Outlet card: single name field in editor.

**Changed**
- Outlet card is now collapsible (same accordion pattern as combined card). Click to expand/collapse details.

### v0.5.0 (2025-03-15)

**Added**
- **New `netio-outlet-card`** — Single-outlet Lovelace card with outlet dropdown, ON/OFF toggle, action buttons, energy metering, and visual card editor.
- **Individual button configuration** — Separate checkboxes for Restart, Short ON, Toggle buttons (replaced single "Show action buttons" toggle).

### v0.4.2 (2025-03-15)

**Fixed**
- **Lovelace card entity discovery** — Card used string matching (`id.includes("netio")`) which failed when entity IDs are based on device name. Now uses `hass.entities` with `platform === "netio"` and groups entities by `device_id`.

### v0.4.1 (2025-03-15)

**Fixed**
- Brand logo/icon not showing in HACS and HA — moved `icon.png` and `logo.png` to the correct location (`custom_components/netio/`)

### v0.4.0 (2025-03-15)

**Added**
- **Per-outlet sub-devices** — Each power output is now registered as its own device in Home Assistant, linked to the parent NETIO device via `via_device`. This allows assigning individual outlets to different rooms.

**Changed**
- New base class `NetioOutputEntity` for all per-outlet entities (switch, output sensors, buttons)
- `NetioEntity` remains for device-level entities (global sensors, digital inputs)
- Entity names simplified (e.g. "Switch", "Restart") since the outlet name is already in the sub-device name

**Migration from v0.3.x:** Remove the integration, restart HA, then re-add it. This ensures the device registry creates the new sub-devices correctly.

### v0.3.6 (2025-03-14)

**Fixed**
- `ImportError: NetioConfigEntry` — all platform files (switch, sensor, binary_sensor, button) still imported the removed `NetioConfigEntry` type alias. Replaced with standard `ConfigEntry` from `homeassistant.config_entries`.

### v0.3.5 (2025-03-14)

**Fixed**
- Python 3.12+ compatibility — removed `type NetioConfigEntry` statement (PEP 695 syntax not supported below Python 3.12). Uses standard `ConfigEntry` directly.

### v0.3.4 (2025-03-14)

**Fixed**
- `SyntaxError` on HA startup caused by Python 3.12+ type alias syntax (`type X = Y`). Replaced with backward-compatible type annotation.

### v0.3.3 (2025-03-14)

**Fixed**
- Lovelace card static path registration for HA 2025.x+ (`StaticPathConfig` API change)
- Fallback to legacy `register_static_path()` for older HA versions

### v0.3.2 (2025-03-14)

**Added**
- Custom Lovelace card with glassmorphism design (inspired by Bubble Card)
- Visual card editor with configuration UI
- Accordion layout, per-output action buttons, energy metering display
- Dark/light theme auto-detection, customizable accent color
- Multilingual support (German / English)

### v0.3.1 (2025-03-14)

**Added**
- Button entities for NETIO output actions: Restart (Short OFF), Short ON, Toggle
- Binary sensor entities for digital inputs (e.g. PowerDIN 4PZ)
- S0 pulse counter sensors for digital inputs

### v0.3.0 (2025-03-14)

**Added**
- Initial release as HACS custom integration
- JSON over HTTP(s) API support (Protocol Version 2.4)
- Switch entities for power output control (on/off)
- Sensor entities for energy metering (current, load, energy, power factor, voltage, frequency)
- Config flow UI with auto-detection of NETIO devices (DHCP via MAC prefix `24:A4:2C`)
- Support for all current and obsolete NETIO products with JSON API

## License

MIT
