# ABB Terra Charger

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![GitHub Release](https://img.shields.io/github/v/release/bekovan/ABB-Terra-charger?sort=semver)](https://github.com/bekovan/ABB-Terra-charger/releases)
[![License: MIT](https://img.shields.io/github/license/bekovan/ABB-Terra-charger.svg)](LICENSE)

A Home Assistant custom integration for ABB Terra AC wallboxes, talking to the
charger over Modbus TCP. Exposes live charging telemetry, a charging current
limit and start/stop controls as native Home Assistant entities.

> Unofficial integration. Not affiliated with or endorsed by ABB.

## Features

- Local polling over Modbus TCP — no cloud, no account — every 8 seconds
- Live three-phase current and voltage, active power and charger state
- `Energy Delivered` accumulates across charging sessions and survives Home Assistant restarts
- Charging state and plug detection as binary sensors
- Settable charging current limit (0–32 A)
- Start / stop charging session buttons and an on/pause charging switch
- Serial number and firmware version reported as device information

## Requirements

- Home Assistant 2026.11.0 or newer
- The built-in **Modbus** integration (declared as a manifest dependency; nothing
  extra to install)
- Modbus TCP enabled on the charger, reachable on your network over a wired
  connection (Modbus over Wi-Fi is not supported)
- Only one Modbus TCP client may connect to the charger at a time

## Installation

### HACS (custom repository)

1. HACS → **Integrations** → ⋮ → **Custom repositories**
2. Add `https://github.com/bekovan/ABB-Terra-charger` with category **Integration**
3. Install **ABB Terra Charger** and restart Home Assistant

Releases are published as the zip asset `abb_terra_charger.zip`; HACS installs
that asset because the repository is not content-in-root.

### Manual

Copy the `abb_terra_charger` folder into `custom_components/`:

```
config/
└── custom_components/
    └── abb_terra_charger/
        ├── __init__.py
        ├── binary_sensor.py
        ├── button.py
        ├── config_flow.py
        ├── const.py
        ├── coordinator.py
        ├── manifest.json
        ├── number.py
        ├── sensor.py
        ├── strings.json
        ├── switch.py
        ├── brand/
        ├── translations/
        └── vendor/
```

Restart Home Assistant.

## Configuration

Add the integration from **Settings → Devices & services → Add integration →
ABB Terra Charger**. The config flow proves the connection by reading a register
before the entry is created, so a wrong host, port or unit ID fails immediately.

| Option | Default | Description |
|---|---|---|
| Host |  | Charger IP address |
| Port | `502` | Modbus TCP port |
| Unit ID | `1` | Modbus unit / slave ID |

One config entry per charger. The entry is titled
`ABB Terra Charger (<host>)`.

## Entities

All entities belong to a single device reporting manufacturer `ABB`, model
`Terra Charger`, plus the serial number and firmware version read from the unit.
Entity IDs derive from the device name when the entities are first created
(typically `abb_terra_charger`); renaming the device later does not rename
existing entity IDs.

### Sensors

| Entity | Unit | Device class | Notes |
|---|---|---|---|
| Serial Number | — | — | Read from the charger |
| Firmware Version | — | — | Read from the charger |
| Error Code | — | — | `0` means no error |
| Socket Lock State | — | — | Raw socket lock state |
| L1 / L2 / L3 Current | A | current | Per-phase current |
| User Set Max Current | A | current | Configured maximum |
| L1 / L2 / L3 Voltage | V | voltage | Per-phase voltage |
| Active Power | W | power | Current charging power |
| Energy Delivered | Wh | energy | Cumulative across sessions, `total_increasing` |
| Charger State | — | enum | Idle, Connected (auth pending), Connected, Connected (no PWM), Charging, Charging Complete, Paused, Other |

### Binary sensors

| Entity | Notes |
|---|---|
| Charging | On while the charger reports an active charging state |
| Plugged In | On while a vehicle is connected |

### Number

| Entity | Range | Unit | Notes |
|---|---|---|---|
| Charging Current Limit | 0–32 | A | Sets the charging current limit |

### Buttons

| Entity | Notes |
|---|---|
| Start Charging Session | Starts a charging session |
| Stop Charging Session | Stops the current session |

### Switch

| Entity | Notes |
|---|---|
| Charging | On when the current limit is above 0; turning it off sets the limit to 0 |

## Energy Delivered

The charger's Modbus map only exposes the energy of the **current session**
(register `401Eh`, Wh), which the charger resets to zero for every new session.
There is no lifetime-total register.

To provide a value that never resets, the integration keeps a running total in
software:

- The total increases by the change in the session register.
- A drop in the register is treated as a new session; the new session value is
  added to the total.
- The total and the last session value are persisted, so they survive Home
  Assistant restarts.
- The sensor uses `state_class: total_increasing` and `device_class: energy`.

Accumulation starts with the first reading after the integration is added; past
sessions are not backfilled. A spurious `0` reading while idle is treated as a
session reset, which adds nothing and does not lower the total.

## Troubleshooting

**"Cannot connect to the charger" during setup**

- Confirm the charger has a wired connection. Modbus over Wi-Fi is not supported.
- Confirm the IP address is reachable (`ping`).
- Confirm Modbus TCP is enabled on the charger and the port is correct (502 by
  default).
- Check the unit ID — the default is 1, but it is configurable per installation.
- Make sure no other Modbus master is already connected; ABB Terra allows a
  single TCP client at a time.

**Entities show as unavailable after working**

The coordinator logs the failure once. Check Home Assistant logs for
`Cannot connect to the ABB Terra Charger at <host>:<port>` and verify the charger
is still on the network.

**Entity IDs changed after renaming the device**

Renaming a device in Home Assistant does not rename existing entities. Update
automations and dashboards to the current entity IDs, or rename the entities
explicitly.

## Disclaimer

Use at your own risk. Writing registers can start or stop a charging session and
change the current limit — verify behaviour with your own hardware before
relying on it. Not affiliated with ABB.

## License

MIT — see [LICENSE](LICENSE).
