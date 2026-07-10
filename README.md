# CcWatch Companion

Minimal data source for the **CC Watch** Garmin watch face.
One Python file, stdlib only. It reads your Claude Code subscription usage
(from the Claude Code login already on your Mac) and gets it to your watch —
in one of two ways:

| Mode | One-liner | Best for |
|---|---|---|
| **Hosted push** (recommended) | `--push <cloud>/wc/report --token <your-token>` | Zero setup — nothing to expose |
| Self-hosted serve | `--token <secret> --port 8399` | You already run your own endpoint |

## Hosted push mode (recommended)

1. Open the free watch cloud <https://139.224.198.39/wc/> → **Create my token**
   (the same token also serves Garmin sleep/dive data for the Dive Buddy faces).
2. On the computer where Claude Code is logged in:

```bash
python3 ccwatch_companion.py --push https://139.224.198.39/wc/report --token <your-token>
```

3. Watch face settings: URL `https://139.224.198.39/wc/watch`, token `<your-token>`.

It reports raw usage every 5 min (`--interval` to change); the cloud renders
fresh reset-countdowns whenever the watch polls. Keep it running with
`launchd` / `systemd` / a tmux pane — whatever you like.

## Self-hosted serve mode

```bash
python3 ccwatch_companion.py --token pick-a-secret --port 8399
# test:
curl "http://localhost:8399/watch?t=pick-a-secret"
```

### Expose it to your phone

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
