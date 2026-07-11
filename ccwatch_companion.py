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

Requirements: macOS (token read from Keychain) or Linux (~/.claude/.credentials.json)
with Claude Code logged in. Native Windows is not supported (WSL works).
Stdlib only — no pip installs.

Keep it running across reboots with one command (installs launchd/systemd service):
    python3 ccwatch_companion.py --push <cloud>/wc/report --token <token> --install
"""
from __future__ import annotations
import argparse, json, os, re, ssl, subprocess, sys, time, urllib.request
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs

KEYCHAIN_SERVICE = "Claude Code-credentials"
USAGE_API_URL = "https://api.anthropic.com/api/oauth/usage"
CACHE_TTL = 240  # seconds — don't hammer the usage API

_cache: dict = {"ts": 0.0, "data": None}


def _oauth_token() -> str | None:
    # macOS: Claude Code stores credentials in the login Keychain
    try:
        raw = subprocess.check_output(
            ["security", "find-generic-password", "-s", KEYCHAIN_SERVICE, "-w"],
            timeout=3, stderr=subprocess.DEVNULL,
        ).decode().strip()
        tok = json.loads(raw).get("claudeAiOauth", {}).get("accessToken")
        if tok:
            return tok
    except Exception:
        pass
    # Linux (and some setups): plain credentials file, same JSON shape
    try:
        raw = Path.home().joinpath(".claude", ".credentials.json").read_text()
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


def push_loop(url: str, token: str, interval: int) -> None:
    """Hosted push mode: report raw usage to the free watch cloud every `interval` seconds.

    Sends raw utilization + reset timestamps (NOT pre-formatted countdowns) so the
    cloud can render fresh countdowns whenever the watch actually polls.
    """
    endpoint = f"{url.rstrip('/')}?t={token}"
    print(f"ccwatch companion PUSH mode → {url} every {interval}s (Ctrl-C to stop)")
    while True:
        u = _usage_cached() or {}
        payload = {
            "five_hour": u.get("five_hour"),
            "seven_day": u.get("seven_day"),
            "five_hour_resets_at": u.get("five_hour_resets_at"),
            "seven_day_resets_at": u.get("seven_day_resets_at"),
            "busy": _busy_count(),
        }
        try:
            req = urllib.request.Request(
                endpoint, data=json.dumps(payload).encode(),
                headers={"Content-Type": "application/json"}, method="POST")
            ctx = ssl.create_default_context()
            try:
                urllib.request.urlopen(req, timeout=10, context=ctx).read()
            except ssl.SSLError:
                # IP-cert endpoints (the free hosted cloud uses a Let's Encrypt IP cert;
                # some Python builds can't verify IP-SAN) — retry unverified rather than die.
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE
                urllib.request.urlopen(req, timeout=10, context=ctx).read()
            print(f"[{time.strftime('%H:%M:%S')}] pushed 5h={payload['five_hour']} "
                  f"7d={payload['seven_day']} busy={payload['busy']}")
        except Exception as e:
            print(f"[{time.strftime('%H:%M:%S')}] push failed ({type(e).__name__}: {e}) — will retry")
        time.sleep(interval)


SERVICE_NAME = "com.ccwatch.companion"


def _install_service(push_url: str, token: str, interval: int) -> None:
    """Install a keep-alive background service so the reporter survives reboots/laptop-lid.
    macOS → launchd LaunchAgent · Linux → systemd user unit. Re-running replaces the old one."""
    script = str(Path(__file__).resolve())
    py = sys.executable or "python3"
    argv = [py, script, "--push", push_url, "--token", token, "--interval", str(interval)]
    if sys.platform == "darwin":
        plist = Path.home() / "Library/LaunchAgents" / f"{SERVICE_NAME}.plist"
        logf = Path.home() / "Library/Logs/ccwatch-companion.log"
        args_xml = "\n".join(f"      <string>{a}</string>" for a in argv)
        plist.parent.mkdir(parents=True, exist_ok=True)
        plist.write_text(f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>{SERVICE_NAME}</string>
  <key>ProgramArguments</key><array>
{args_xml}
  </array>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
  <key>StandardOutPath</key><string>{logf}</string>
  <key>StandardErrorPath</key><string>{logf}</string>
</dict></plist>
""")
        uid = os.getuid()
        subprocess.run(["launchctl", "bootout", f"gui/{uid}", str(plist)],
                       capture_output=True)  # replace old install, ok if absent
        r = subprocess.run(["launchctl", "bootstrap", f"gui/{uid}", str(plist)],
                           capture_output=True, text=True)
        if r.returncode != 0:
            print(f"launchctl bootstrap failed: {r.stderr.strip()}")
            sys.exit(1)
        print(f"✓ installed launchd service {SERVICE_NAME}\n  runs at login, restarts if it dies"
              f"\n  log: {logf}\n  uninstall: python3 {script} --uninstall")
    elif sys.platform.startswith("linux"):
        unit = Path.home() / ".config/systemd/user" / "ccwatch-companion.service"
        unit.parent.mkdir(parents=True, exist_ok=True)
        exec_line = " ".join(f'"{a}"' if " " in a else a for a in argv)
        unit.write_text(f"""[Unit]
Description=CcWatch companion usage reporter

[Service]
ExecStart={exec_line}
Restart=always
RestartSec=10

[Install]
WantedBy=default.target
""")
        for cmd in (["systemctl", "--user", "daemon-reload"],
                    ["systemctl", "--user", "enable", "--now", "ccwatch-companion"]):
            r = subprocess.run(cmd, capture_output=True, text=True)
            if r.returncode != 0:
                print(f"{' '.join(cmd)} failed: {r.stderr.strip()}")
                sys.exit(1)
        print("✓ installed systemd user service ccwatch-companion\n"
              f"  status: systemctl --user status ccwatch-companion\n"
              f"  uninstall: python3 {script} --uninstall")
    else:
        print("--install supports macOS (launchd) and Linux (systemd) only.\n"
              "On other systems keep the --push command running yourself.")
        sys.exit(1)


def _uninstall_service() -> None:
    if sys.platform == "darwin":
        plist = Path.home() / "Library/LaunchAgents" / f"{SERVICE_NAME}.plist"
        subprocess.run(["launchctl", "bootout", f"gui/{os.getuid()}", str(plist)],
                       capture_output=True)
        if plist.exists():
            plist.unlink()
        print(f"✓ removed {SERVICE_NAME}")
    elif sys.platform.startswith("linux"):
        subprocess.run(["systemctl", "--user", "disable", "--now", "ccwatch-companion"],
                       capture_output=True)
        unit = Path.home() / ".config/systemd/user" / "ccwatch-companion.service"
        if unit.exists():
            unit.unlink()
        subprocess.run(["systemctl", "--user", "daemon-reload"], capture_output=True)
        print("✓ removed ccwatch-companion")
    else:
        print("nothing to uninstall on this platform")


def main():
    ap = argparse.ArgumentParser(description="CcWatch companion (self-hosted serve OR hosted push)")
    ap.add_argument("--token",
                    help="serve mode: shared secret the watch sends as ?t= · "
                         "push mode: your personal token from the hosted cloud")
    ap.add_argument("--port", type=int, default=8399)
    ap.add_argument("--host", default="0.0.0.0")
    ap.add_argument("--push", metavar="URL", default="",
                    help="hosted push mode: report usage to this /report endpoint "
                         "(e.g. https://139.224.198.39/wc/report) instead of serving locally")
    ap.add_argument("--interval", type=int, default=300,
                    help="push mode report interval in seconds (default 300)")
    ap.add_argument("--install", action="store_true",
                    help="with --push/--token: install a background service (launchd/systemd) "
                         "so the reporter keeps running after reboot, then exit")
    ap.add_argument("--uninstall", action="store_true",
                    help="remove the background service installed by --install")
    args = ap.parse_args()
    if args.uninstall:
        _uninstall_service()
        return
    if not args.token:
        ap.error("--token is required")
    if args.install:
        if not args.push:
            ap.error("--install needs --push URL (hosted push mode)")
        _install_service(args.push, args.token, max(60, args.interval))
        return
    if args.push:
        push_loop(args.push, args.token, max(60, args.interval))
        return
    srv = ThreadingHTTPServer((args.host, args.port), Handler)
    srv.watch_token = args.token  # type: ignore[attr-defined]
    print(f"ccwatch companion on http://{args.host}:{args.port}/watch?t=***  (Ctrl-C to stop)")
    srv.serve_forever()


if __name__ == "__main__":
    main()
