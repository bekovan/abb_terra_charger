# ABB Terra Charger

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![GitHub Release](https://img.shields.io/github/v/release/bekovan/ABB-Terra-AC?sort=semver)](https://github.com/bekovan/ABB-Terra-AC/releases)
[![License: MIT](https://img.shields.io/github/license/bekovan/ABB-Terra-AC.svg)](LICENSE)

A Home Assistant custom integration for ABB Terra AC wallboxes, talking to the
charger over Modbus TCP. Exposes live charging telemetry, a charging current
limit and start/stop controls as native Home Assistant entities.

> Unofficial integration. Not affiliated with or endorsed by ABB.

## Features

- Local polling over Modbus TCP (no cloud, no account) — default interval 15 s
- Live three-phase current and voltage, active power and session energy
- Charging state and plug detection as binary input, facilitates integration to Solar Energy Management for Home Assistant 
- Settable charging current limit
- Start / stop charging session buttons
- Serial number and firmware version reported as device information

## Requirements

- Home Assistant 2026.10 or newer (uses `modbus.async_get_unit` and
  `async_get_temporary_unit`)
- The built-in **Modbus** integration (declared as a manifest dependency; nothing
  extra to install)
- Modbus TCP enabled on the charger, reachable on your network


## Installation

### HACS (custom repository)

1. HACS → **Integrations** → ⋮ → **Custom repositories**
2. Add `https://github.com/bekovan/ABB-Terra-AC` with category **Integration**
3. Install **ABB Terra Charger** and restart Home Assistant


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
        ├── brand/
        ├── translations/
        └── vendor/
```

Restart Home Assistant.

## Configuration

Add the integration from **Settings → Devices & services → Add integration →
ABB Terra Charger**. The config flow proves the connection by reading a register
before the entry is created, so a wrong host/port/unit ID fails immediately.

| Option | Default | Description |
|---|---|---|
| Host |  | Charger IP address |
| Port | `502` | Modbus TCP port |
| Unit ID | `1` | Modbus unit / slave ID |

One config entry per charger. The entry is titled
`ABB Terra Charger (<host>)`.

## Entities

Entity IDs are prefixed with `abb_terra_charger` because entities use the device
name. All entities belong to a single device reporting manufacturer `ABB`,
model `Terra Charger`, plus the serial number and firmware version read from the
unit.


## Troubleshooting

**"Cannot connect to the charger" during setup**

- Confirm charger has a wired connection. Modbus over WIFI is not supported
Confirm the IP address is reachable (`ping`).
- Confirm Modbus TCP is enabled on the charger and the port is correct (502 by
  default).
- Check the unit ID — the default is 1, but it is configurable per installation.
- Make sure no other Modbus master is already connected; ABB Terra allow a
  single TCP client at a time.

**Entities show as unavailable after working**

The coordinator logs the failure once. Check Home Assistant logs for
`Cannot connect to the ABB Terra Charger at <host>:<port>` and verify the charger
is still on the network.

## Disclaimer

Use at your own risk. Writing registers can start or stop a charging session and
change the current limit — verify behaviour with your own hardware before
relying on it. Not affiliated with ABB.

## License

MIT — see [LICENSE](LICENSE).
