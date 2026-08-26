# govee-mcp

MCP server for controlling Govee smart lights. Turn lights on/off, set brightness, color, and color temperature via Claude.

## Overview

**govee-mcp** is a FastMCP server that controls Govee lights **LAN-first, with the cloud REST API as
a fallback** — a local command is ~10ms, has no rate limit, and survives a Govee cloud outage.

The device inventory lives in Supabase `govee_devices`, synced from the Govee account by
`sync_devices.py`. `GOVEE_LIGHT_*` env vars are the fallback for when Supabase is unreachable.

## Setup

1. Copy `.env.example` → `.env-govee` and add `GOVEE_API_KEY` (needed for the cloud fallback and for
   `sync_devices.py`).
2. Seed the inventory: `python sync_devices.py` (or `--loop` on an always-on machine to refresh every
   ~30 min — the `jared-voice` Fly app does this).
3. Register the MCP server in Claude Code settings.

See [CLAUDE.md](CLAUDE.md) before changing any of it.

## MCP Tools

| Tool | Parameters | Purpose |
|------|-----------|---------|
| `set_power(light, state)` | light name, "on"/"off" | Turn light on/off |
| `set_brightness(light, brightness)` | light name, 1-100 | Set brightness |
| `set_color(light, color)` | light name, color spec | Set RGB color |
| `set_color_temp(light, kelvin)` | light name, 2000-9000K | Set color temperature |
| `list_lights()` | — | List all configured lights |

## Color Specifications

Colors can be specified as:
- **Names:** `red`, `blue`, `green`, `purple`, `orange`, `pink`, `cyan`, `white`, `warm white`, `yellow`, `teal`, `lavender`, `coral`, `lime`, `gold`, `indigo`, `magenta`
- **Hex:** `#FF0000`
- **RGB:** `255,0,0`

## Architecture

- `govee_mcp.py` — single-file FastMCP server. LAN: multicast scan to `239.255.255.250:4001`,
  replies on `:4002`, commands to `<device_ip>:4003`, with a 30s cache of each discovered IP.
  Cloud fallback: Govee's `/router/api/v1/device/control`.
- `sync_devices.py` — pulls `/user/devices` into Supabase `govee_devices`, keeping only real lights
  (a `light` type with a brightness capability, which drops `powerSwitch`-only ghosts) under
  slugified stable keys. Devices off the account are removed; the `hidden` flag survives a sync.

## Related

- **Lights Control:** [home_control](https://github.com/JJGantt/home_control) — Voice/multi-device home automation
