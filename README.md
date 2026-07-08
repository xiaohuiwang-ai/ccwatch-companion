# CcWatch Companion

Minimal self-hosted data source for the **CC Watch** Garmin watch face.
One Python file, stdlib only. It reads your Claude Code subscription usage
(from the Claude Code login already on your Mac) and serves the tiny JSON
endpoint the watch face polls every 10 minutes.

## Quick start (macOS, Claude Code installed & logged in)

```bash
python3 ccwatch_companion.py --token pick-a-secret --port 8399
# test:
curl "http://localhost:8399/watch?t=pick-a-secret"
```

## Expose it to your phone

The watch fetches through Garmin Connect Mobile on your phone, so the URL must
be reachable from the phone's network. Any of:

- **Tailscale Funnel / Serve** (easiest HTTPS)
- **Cloudflare Tunnel**
- Your own reverse proxy / VPS port-forward

## Point the watch face at it

Garmin Connect Mobile → your device → Connect IQ apps → **CC Watch** → Settings:

| Setting | Value |
|---|---|
| Hub /watch URL | `https://your-host/watch` |
| Watch token | `pick-a-secret` |

## What the face shows

- `5H 12% 3H33M` — five-hour window: used % + time to reset
- `7D 64% 2D13H` — weekly window: used % + time to reset
- Pixel crab drums while `busy > 0` (count of running `claude` CLI processes)
- Link light: green = data fresh (<25 min), yellow <60 min, red = stale/broken

## Payload contract (`GET /watch?t=<token>`)

```json
{"ok": true, "ts": 1783500000,
 "fh_used": 12, "wk_used": 64,
 "fh_resets": "3h33m", "wk_resets": "2d13h",
 "busy": 1, "pending": 0, "done_str": ""}
```

Anything speaking this contract works — the reference ccbridge hub serves a
richer version of the same endpoint.
