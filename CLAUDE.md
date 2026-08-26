# Working in govee-mcp

## The light list comes from Supabase, not from `.env-govee`

`_load_lights()` reads `govee_devices` (rows where `hidden` is false) and only falls back to
`GOVEE_LIGHT_*` env vars when `SUPABASE_KEY` is unset or the read fails. So a new lamp appears by
running `sync_devices.py`, not by editing the env file — and hiding one is the `hidden` column, which
`sync_devices.py` deliberately preserves across syncs.

`LIGHTS` is built **once at import**. A freshly synced or unhidden device is invisible until the MCP
server is restarted.

## Transport is LAN-first, and the LAN half only works from home

Each command multicasts a scan (`239.255.255.250:4001`, replies on `:4002`) and, if the lamp answers,
sends straight to `<device_ip>:4003` — ~10ms, no rate limit, immune to a Govee cloud outage. The
cloud REST API is the fallback for when the lamp doesn't answer.

Two consequences worth knowing before debugging "it's slow" or "it doesn't work":

- The process has to be on the same network as the lamp and able to receive UDP on 4002. The copy
  running inside the `jared-voice` Fly app never gets a LAN answer and always takes the cloud path.
- LAN control is a per-lamp setting in the Govee app. A lamp with it off silently uses the cloud.

## Fly runs a copy, and it is not this checkout

`voice-pipeline/server/assemble.sh` copies `govee_mcp.py` and `sync_devices.py` into the `jared-voice`
image. A change here does not reach Fly until that app is reassembled and redeployed.

## Secrets

`GOVEE_API_KEY` lives in the gitignored `.env-govee` (template: `.env.example`). Without it the LAN
path still works and the cloud fallback does not — so an expired key looks like "some lights work".
