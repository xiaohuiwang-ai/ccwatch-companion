#!/usr/bin/env python3
"""
CcWatch companion — minimal self-hosted data source for the CC Watch Garmin face.

Reads YOUR Claude Code subscription usage (via the Claude Code OAuth token already
on your Mac) and serves it as the tiny JSON endpoint the watch face polls.

Usage:
    python3 ccwatch_companion.py --token <your-secret> [--port 8399]

Then expose http://<your-host>:8399/watch to the internet however you like
(Tailscale Funnel / Cloudflare Tunnel / reverse proxy — HTTPS recommended;
Garmin phones require a reachable URL), and in Garmin Connect Mobile set the
watch face settings:
    Hub /watch URL  = https://your-host/watch
    Watch token     = <your-secret>

Requirements: macOS with Claude Code logged in (token read from Keychain).
Stdlib only — no pip installs.
"""
from __future__ import annotations
import argparse, json, re, ssl, subprocess, time, urllib.request
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

KEYCHAIN_SERVICE = "Claude Code-credentials"
USAGE_API_URL = "https://api.anthropic.com/api/oauth/usage"
CACHE_TTL = 240  # seconds — don't hammer the usage API

_cache: dict = {"ts": 0.0, "data": None}


def _oauth_token() -> str | None:
    try:
        raw = subprocess.check_output(
            ["security", "find-generic-password", "-s", KEYCHAIN_SERVICE, "-w"],
            timeout=3, stderr=subprocess.DEVNULL,
        ).decode().strip()
        return json.loads(raw).get("claudeAiOauth", {}).get("accessToken")
    except Exception:
        return None


def _fetch_usage() -> dict | None:
    tok = _oauth_token()
    if not tok:
        return None
    try:
        req = urllib.request.Request(USAGE_API_URL, headers={
            "Authorization": f"Bearer {tok}",
            "anthropic-beta": "oauth-2025-04-20",
            "User-Agent": "ccwatch-companion/1.0",
        })
        data = json.loads(urllib.request.urlopen(
            req, timeout=8, context=ssl.create_default_context()).read())
        fh, sd = data.get("five_hour") or {}, data.get("seven_day") or {}
        return {
            "five_hour": fh.get("utilization"),
            "seven_day": sd.get("utilization"),
            "five_hour_resets_at": fh.get("resets_at"),
            "seven_day_resets_at": sd.get("resets_at"),
        }
    except Exception:
        return None


def _usage_cached() -> dict | None:
    if time.time() - _cache["ts"] < CACHE_TTL and _cache["data"]:
        return _cache["data"]
    u = _fetch_usage()
    if u:
        _cache.update(ts=time.time(), data=u)
    return _cache["data"]


def _compact_until(iso: str | None) -> str:
    """ISO reset time → compact remaining: 45m / 1h31m / 34h (≥10h drops minutes)."""
    try:
        dt = datetime.fromisoformat((iso or "").replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        secs = (dt - datetime.now(timezone.utc)).total_seconds()
        if secs <= 0:
            return "0m"
        h, m = int(secs // 3600), int(secs % 3600 // 60)
        if h >= 10:
            return f"{h}h"
        return f"{h}h{m}m" if h else f"{m}m"
    except Exception:
        return ""


def _weekly_two_seg(s: str) -> str:
    """Weekly countdown: ≥24h → '2d13h' so it pairs with the 5h window's '2h35m'."""
    m = re.match(r"^(\d+)h(?:\d+m)?$", s or "")
    if not m:
        return s or ""
    h = int(m.group(1))
    return s if h < 24 else f"{h // 24}d{h % 24}h"


def _busy_count() -> int:
    """Rough 'agents busy' signal: number of running `claude` CLI processes."""
    try:
        out = subprocess.check_output(["pgrep", "-x", "claude"],
                                      timeout=2, stderr=subprocess.DEVNULL)
        return len(out.decode().split())
    except Exception:
        return 0


def build_payload() -> dict:
    u = _usage_cached() or {}
    fh, sd = u.get("five_hour"), u.get("seven_day")
    fr = _compact_until(u.get("five_hour_resets_at"))
    wr = _weekly_two_seg(_compact_until(u.get("seven_day_resets_at")))
    return {
        "ok": True,
        "ts": int(time.time()),
        "fh_used": round(fh) if fh is not None else None,
        "wk_used": round(sd) if sd is not None else None,
        "fh_resets": fr,
        "wk_resets": wr,
        "busy": _busy_count(),
        "pending": 0,
        "done_str": "",
    }


class Handler(BaseHTTPRequestHandler):
    server_version = "ccwatch-companion/1.0"

    def do_GET(self):  # noqa: N802
        url = urlparse(self.path)
        if url.path != "/watch":
            self.send_error(404)
            return
        q = parse_qs(url.query)
        if q.get("t", [""])[0] != self.server.watch_token:  # type: ignore[attr-defined]
            self._json({"ok": False, "err": "bad token"}, 403)
            return
        self._json(build_payload())

    def _json(self, obj: dict, status: int = 200):
        body = json.dumps(obj).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        print(f"[{time.strftime('%H:%M:%S')}] {self.address_string()} {fmt % args}")


def main():
    ap = argparse.ArgumentParser(description="CcWatch companion server")
    ap.add_argument("--token", required=True, help="shared secret the watch sends as ?t=")
    ap.add_argument("--port", type=int, default=8399)
    ap.add_argument("--host", default="0.0.0.0")
    args = ap.parse_args()
    srv = ThreadingHTTPServer((args.host, args.port), Handler)
    srv.watch_token = args.token  # type: ignore[attr-defined]
    print(f"ccwatch companion on http://{args.host}:{args.port}/watch?t=***  (Ctrl-C to stop)")
    srv.serve_forever()


if __name__ == "__main__":
    main()
