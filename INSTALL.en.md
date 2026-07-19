# CcWatch — Install Guide

> Supported device: **Garmin Descent G2** (more models coming)
> CcWatch = a Garmin watch face for Claude Code users: sleep/body data + Claude usage rings.

## Option A (recommended): Connect IQ Store

1. Open the **Connect IQ Store** app on your phone
2. Search **CcWatch**, install — the watch receives it automatically
3. On the watch: long-press MENU → "Watch Face" → select CcWatch
4. Jump to "Pair" below

## Option B: Sideload (test builds / no store access)

With `CcWatch.prg` on your computer, connect the watch via the **original cable**:

**Mac** (install free OpenMTP first — macOS cannot see the watch storage): https://openmtp.ganeshrvel.com → open it → watch storage → `GARMIN/APPS` → drag `CcWatch.prg` in, unplug.
**Windows**: "This PC" → Garmin device → `GARMIN/APPS` → copy, unplug.

Then long-press MENU → "Watch Face" → **CcWatch**.

## Pair (30 seconds)

On first use the face shows **PAIR CODE + 6 digits**.

1. Open **watch.xiaohuiwangai.cn/cc** on your phone and follow the stepper
2. At step 2, enter the 6-digit code — your private account is created automatically (the step-1 token is generated at the same time)
3. Step 3 — link your Garmin account (on the account page): China or International region, Garmin credentials (used once, **never stored**; 2FA supported)
4. Leave the watch alone: it activates within 10 minutes, sleep/body data appears within ~20-30 minutes

## Optional: Claude usage rings (needs your computer)

The Claude usage rings need your computer to report every 5 minutes:

```bash
git clone https://github.com/xiaohuiwang-ai/ccwatch-companion
cd ccwatch-companion
python3 ccwatch_companion.py --push https://watch.xiaohuiwangai.cn/wc/report --token <your-token>
# install as a daemon (macOS launchd / Linux systemd):
python3 ccwatch_companion.py --install --push https://watch.xiaohuiwangai.cn/wc/report --token <your-token>
```

Your token is shown on the watch.xiaohuiwangai.cn/cc account page. Without the companion everything else still works — the Claude rings just show "?".

## FAQ

| Symptom | Cause / fix |
|---|---|
| Pair code never disappears | The face checks every 10 minutes — wait for the next cycle |
| Pair code expired (1 h) | Re-open the face for a fresh code |
| OpenMTP does not see the watch | Original cable; replug once |
| Claude rings show "?" | Companion not running, or no report for 20+ min |
| Data shows "--" | First pull can take up to 30 min |

Issues: https://github.com/xiaohuiwang-ai/ccwatch-companion
