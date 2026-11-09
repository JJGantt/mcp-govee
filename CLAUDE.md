# Working in govee-mcp

## The light list comes from Supabase, not from `.env-govee`

`_load_lights()` reads `govee_devices` (rows where `hidden` is false) and only falls back to
`GOVEE_LIGHT_*` env vars when `SUPABASE_KEY` is unset or the read fails. So a new lamp appears by
running `sync_devices.py`, not by editing the env file — and hiding one is the `hidden` column, which
`sync_devices.py` deliberately preserves across syncs.

`list_lights` re-reads the inventory every call, and a command naming a light the server does not
know re-reads it once before refusing, so a newly synced lamp works without a restart. A lamp hidden
after start stays controllable by name until the server restarts.

## Transport is LAN-first, and the LAN half only works from home

Each command multicasts a scan (`239.255.255.250:4001`, replies on `:4002`) and, if the lamp answers,
sends straight to `<device_ip>:4003` — ~10ms, no rate limit, immune to a Govee cloud outage. The
cloud REST API is the fallback for when the lamp doesn't answer.

Two consequences worth knowing before debugging "it's slow" or "it doesn't work":

- The process has to be on the same network as the lamp and able to receive UDP on 4002. A host that
  never is sets `GOVEE_LAN=0`, which skips the scan: otherwise every command spends ~1.2s waiting
  for a scan that cannot be answered before it reaches the cloud. The `jared-voice-worker` Fly app
  sets it in its Dockerfile.
- LAN control is a per-lamp setting in the Govee app. A lamp with it off silently uses the cloud.
  None of the lamps answer a LAN scan or a unicast `devStatus` from the Pi, so in practice every
  command and every state read goes through the cloud.

## Cloud state is an echo, not a reading

For these lamps the cloud's `/device/state` power and brightness are the last value commanded: send
brightness 60 and the next read says 60, whether or not the bulb changed. A light that missed a
command therefore reads as obeying it. `list_lights` labels cloud lines "last commanded, not
measured" and a cloud command says it was accepted, not confirmed, so the caller does not report
either as what the light is doing. Only a LAN `devStatus` reply is a real reading.

## The cloud is slow, and its failures must carry a message

The Govee cloud regularly takes several seconds to answer a command. Calls go through
`_cloud_post`, with a 15s timeout and one retry on a timeout or connection failure. httpx's default
5s timeout is too short, and its `ReadTimeout` has an empty message — a tool that lets it escape fails
as a bare `Error executing tool set_color:` with nothing to say why. Every cloud failure, a rejected
command included, raises `GoveeError` naming what went wrong, so the caller sees a real error rather
than a success-shaped string.

## Fly runs copies, and they are not this checkout

`voice-pipeline/fly-worker/deploy.sh` copies `govee_mcp.py` into the `jared-voice-worker` image — the
voice worker that claims requests first, so it is the copy that answers most light commands.
`voice-pipeline/server/assemble.sh` copies `sync_devices.py` into the `jared-voice` image. A change
here does not reach Fly until the app is redeployed with that script.

## Secrets

`GOVEE_API_KEY` lives in the gitignored `.env-govee` (template: `.env.example`). Without it the LAN
path still works and the cloud fallback does not — so an expired key looks like "some lights work".
