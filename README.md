# govee-mcp

MCP server for controlling Govee smart lights. Turn lights on/off, set brightness, color, and color temperature via Claude.

## Overview

**govee-mcp** is a FastMCP server that communicates with Govee smart lights via their HTTP API. Lights are configured in a gitignored `.env-govee` file and exposed as MCP tools.

Perfect for adding smart home control to your Claude conversations.

## Setup

1. Copy `.env-govee.example` → `.env-govee`
2. Add your Govee API key and light configurations:

```bash
GOVEE_API_KEY=your_key_here

# Format: GOVEE_LIGHT_<name>=<sku>,<device_id>,<display_name>
GOVEE_LIGHT_bedroom_lamp=H6159,aabbccdd:eeffgghh,Bedroom Lamp
GOVEE_LIGHT_kitchen_lights=H6052,11223344:55667788,Kitchen
```

3. Register the MCP server in Claude Code settings

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

- `govee_mcp.py` — Single-file FastMCP server
- Uses Govee's `/router/api/v1/device/control` endpoint
- Async HTTP client for fast control

## Related

- **Lights Control:** [home_control](https://github.com/JJGantt/home_control) — Voice/multi-device home automation
