#!/usr/bin/env python3
"""MCP server for controlling Govee smart lights."""

import os
import uuid
from pathlib import Path

import httpx
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

load_dotenv(Path(__file__).parent / ".env-govee")

API_KEY = os.environ["GOVEE_API_KEY"]
BASE_URL = "https://openapi.api.govee.com/router/api/v1"
HEADERS = {
    "Content-Type": "application/json",
    "Govee-API-Key": API_KEY,
}

# Load lights from env: GOVEE_LIGHT_<NAME>=<sku>,<device_id>,<display_name>
LIGHTS = {}
for key, val in os.environ.items():
    if key.startswith("GOVEE_LIGHT_"):
        name = key[len("GOVEE_LIGHT_"):].lower()
        sku, device, display = val.split(",", 2)
        LIGHTS[name] = {"sku": sku.strip(), "device": device.strip(), "name": display.strip()}

NAMED_COLORS = {
    "red": (255, 0, 0),
    "green": (0, 200, 0),
    "blue": (0, 0, 255),
    "white": (255, 255, 255),
    "warm white": (255, 200, 120),
    "yellow": (255, 220, 0),
    "orange": (255, 100, 0),
    "purple": (140, 0, 255),
    "pink": (255, 60, 180),
    "cyan": (0, 220, 255),
    "magenta": (255, 0, 200),
    "teal": (0, 180, 150),
    "lavender": (160, 120, 255),
    "coral": (255, 80, 60),
    "lime": (120, 255, 0),
    "gold": (255, 180, 0),
    "indigo": (75, 0, 200),
}


def rgb_to_int(r: int, g: int, b: int) -> int:
    return (r << 16) | (g << 8) | b


def parse_color(color_str: str) -> int:
    s = color_str.strip().lower()
    if s in NAMED_COLORS:
        return rgb_to_int(*NAMED_COLORS[s])
    if s.startswith("#"):
        h = s[1:]
        return rgb_to_int(int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))
    parts = s.split(",")
    if len(parts) == 3:
        return rgb_to_int(*[int(p.strip()) for p in parts])
    raise ValueError(
        f"Unknown color '{color_str}'. Use a name (blue, red, purple…), hex (#FF0000), or r,g,b values."
    )


async def _control(sku: str, device: str, cap_type: str, instance: str, value) -> dict:
    payload = {
        "requestId": str(uuid.uuid4()),
        "payload": {
            "sku": sku,
            "device": device,
            "capability": {"type": cap_type, "instance": instance, "value": value},
        },
    }
    async with httpx.AsyncClient() as client:
        r = await client.post(f"{BASE_URL}/device/control", json=payload, headers=HEADERS)
        return r.json()


async def _get_state(sku: str, device: str) -> dict:
    payload = {
        "requestId": str(uuid.uuid4()),
        "payload": {"sku": sku, "device": device},
    }
    async with httpx.AsyncClient() as client:
        r = await client.post(f"{BASE_URL}/device/state", json=payload, headers=HEADERS)
        data = r.json()
        return {c["instance"]: c["state"]["value"] for c in data["payload"]["capabilities"]}


mcp = FastMCP("govee-lights")


@mcp.tool()
async def list_lights() -> str:
    """List all configured lights and their current state (online, power, brightness)."""
    lines = []
    for name, info in LIGHTS.items():
        state = await _get_state(info["sku"], info["device"])
        online = state.get("online", False)
        power = "on" if state.get("powerSwitch") == 1 else "off"
        brightness = state.get("brightness", "?")
        lines.append(f"{name} ({info['name']}): online={online}, power={power}, brightness={brightness}%")
    return "\n".join(lines)


@mcp.tool()
async def set_power(light: str, state: str) -> str:
    """Turn a light on or off.

    Args:
        light: Light name (e.g. 'office_lamp')
        state: 'on' or 'off'
    """
    if light not in LIGHTS:
        return f"Unknown light '{light}'. Available: {list(LIGHTS.keys())}"
    info = LIGHTS[light]
    value = 1 if state.lower() in ("on", "1", "true") else 0
    result = await _control(info["sku"], info["device"], "devices.capabilities.on_off", "powerSwitch", value)
    return f"Turned {info['name']} {state}." if result.get("code") == 200 else str(result)


@mcp.tool()
async def set_brightness(light: str, brightness: int) -> str:
    """Set brightness of a light.

    Args:
        light: Light name (e.g. 'office_lamp')
        brightness: 1–100
    """
    if light not in LIGHTS:
        return f"Unknown light '{light}'. Available: {list(LIGHTS.keys())}"
    info = LIGHTS[light]
    brightness = max(1, min(100, brightness))
    result = await _control(info["sku"], info["device"], "devices.capabilities.range", "brightness", brightness)
    return f"Set {info['name']} brightness to {brightness}%." if result.get("code") == 200 else str(result)


@mcp.tool()
async def set_color(light: str, color: str) -> str:
    """Set the color of a light.

    Args:
        light: Light name (e.g. 'office_lamp')
        color: Color name (red, blue, green, purple, orange, pink, cyan, white, warm white,
               yellow, teal, lavender, coral, lime, gold, indigo, magenta),
               hex string (#FF0000), or r,g,b values (255,0,0)
    """
    if light not in LIGHTS:
        return f"Unknown light '{light}'. Available: {list(LIGHTS.keys())}"
    info = LIGHTS[light]
    try:
        color_int = parse_color(color)
    except ValueError as e:
        return str(e)
    result = await _control(info["sku"], info["device"], "devices.capabilities.color_setting", "colorRgb", color_int)
    return f"Set {info['name']} to {color}." if result.get("code") == 200 else str(result)


@mcp.tool()
async def set_color_temp(light: str, kelvin: int) -> str:
    """Set color temperature of a light in Kelvin. 2000K = warm/candlelight, 4000K = neutral, 6500K = daylight, 9000K = cool blue-white.

    Args:
        light: Light name (e.g. 'office_lamp')
        kelvin: Color temperature in Kelvin (2000–9000)
    """
    if light not in LIGHTS:
        return f"Unknown light '{light}'. Available: {list(LIGHTS.keys())}"
    info = LIGHTS[light]
    kelvin = max(2000, min(9000, kelvin))
    result = await _control(info["sku"], info["device"], "devices.capabilities.color_setting", "colorTemperatureK", kelvin)
    return f"Set {info['name']} color temperature to {kelvin}K." if result.get("code") == 200 else str(result)


if __name__ == "__main__":
    mcp.run()
