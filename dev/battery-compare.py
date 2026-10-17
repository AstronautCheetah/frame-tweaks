#!/usr/bin/env python3
"""Battery levels side by side: the battery's own fuel gauge (what KDE, Frame Tweaks and the charge
limit read) and SteamVR's (what Steam's dashboard shows), to work out how Steam converts one into
the other. On 2026-10-17 Steam read 8 points more (74→82 up to 78→86): "+8" and "÷ 0.9" both fit
that, and part only at low charge (at 20%: 28 or 22).

  dev/battery-compare.py record      one line into the log (the timer runs it every 5 minutes)
  dev/battery-compare.py install     the user timer that records (ft-battery-compare); uninstall
  dev/battery-compare.py report      the readings so far, and how well each formula fits them

Run it with a Python that has openvr (~/.local/share/arrowpad/venv/bin/python). The log:
~/.local/state/frame-tweaks/logs/battery-compare.tsv. SteamVR isn't started for it: while it
isn't running, a reading has the gauge only."""
import glob
import subprocess
import sys
import time
from pathlib import Path

LOG = Path.home() / ".local/state/frame-tweaks/logs/battery-compare.tsv"
UNITS = Path.home() / ".config/systemd/user"
NAME = "ft-battery-compare"
PYTHON = Path.home() / ".local/share/arrowpad/venv/bin/python"
MODELS = {"+8": lambda g: min(100.0, g + 8), "÷ 0.9": lambda g: min(100.0, g / 0.9)}


def gauge():
    """(capacity %, charge_now/charge_full %, status) of the battery, or None."""
    for d in sorted(glob.glob("/sys/class/power_supply/*")):
        try:
            if Path(d, "type").read_text().strip() != "Battery":
                continue
            cap = int(Path(d, "capacity").read_text())
            fine = 100 * int(Path(d, "charge_now").read_text()) / int(Path(d, "charge_full").read_text())
            return cap, round(fine, 2), Path(d, "status").read_text().strip()
        except (OSError, ValueError, ZeroDivisionError):
            continue
    return None


def steamvr():
    """SteamVR's battery level for the headset (%), or None (SteamVR not running, no openvr)."""
    try:
        import openvr
        openvr.init(openvr.VRApplication_Background)        # (fails rather than start SteamVR)
    except Exception:
        return None
    try:
        return round(100 * openvr.VRSystem().getFloatTrackedDeviceProperty(
            openvr.k_unTrackedDeviceIndex_Hmd, openvr.Prop_DeviceBatteryPercentage_Float), 2)
    except Exception:
        return None
    finally:
        openvr.shutdown()


def record():
    g = gauge()
    if g is None:
        return
    vr = steamvr()
    LOG.parent.mkdir(parents=True, exist_ok=True)
    new = not LOG.exists()
    with LOG.open("a") as f:
        if new:
            f.write("time\tgauge\tgauge_fine\tstatus\tsteamvr\n")
        f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')}\t{g[0]}\t{g[1]}\t{g[2]}\t{'' if vr is None else vr}\n")


def install():
    UNITS.mkdir(parents=True, exist_ok=True)
    (UNITS / f"{NAME}.service").write_text(
        "[Unit]\nDescription=Frame Tweaks dev: battery gauge vs SteamVR's level (dev/battery-compare.py)\n\n"
        f"[Service]\nType=oneshot\nNice=19\nExecStart={PYTHON} {Path(__file__).resolve()} record\n")
    (UNITS / f"{NAME}.timer").write_text(
        "[Unit]\nDescription=Frame Tweaks dev: battery gauge vs SteamVR's level, every 5 minutes\n\n"
        "[Timer]\nOnBootSec=2min\nOnUnitActiveSec=5min\nAccuracySec=30s\n\n[Install]\nWantedBy=timers.target\n")
    subprocess.run(["systemctl", "--user", "daemon-reload"], check=True)
    subprocess.run(["systemctl", "--user", "enable", "--now", f"{NAME}.timer"], check=True)
    print(f"recording every 5 minutes into {LOG}")


def uninstall():
    subprocess.run(["systemctl", "--user", "disable", "--now", f"{NAME}.timer"], check=False)
    for f in (UNITS / f"{NAME}.service", UNITS / f"{NAME}.timer"):
        f.unlink(missing_ok=True)
    subprocess.run(["systemctl", "--user", "daemon-reload"], check=False)
    print(f"stopped (the log stays: {LOG})")


def report():
    if not LOG.exists():
        sys.exit(f"nothing recorded yet ({LOG})")
    rows = []
    for line in LOG.read_text().splitlines()[1:]:
        p = line.split("\t")
        if len(p) == 5 and p[4]:
            rows.append((int(p[1]), float(p[4])))
    if not rows:
        sys.exit("no readings with SteamVR running yet")
    pairs = sorted(set(rows))
    print(f"{len(rows)} readings with SteamVR; gauge {pairs[0][0]}–{pairs[-1][0]}%")
    print("gauge → SteamVR: " + ", ".join(f"{g}→{v:g}" for g, v in pairs))
    for name, f in MODELS.items():
        # (SteamVR reports whole numbers: within a point, rounded or cut, is a fit)
        off = [abs(f(g) - v) for g, v in rows]
        print(f"  {name:6} misses by up to {max(off):.2f} points; {sum(o < 1 for o in off)} of {len(rows)} within a point")
    if len({g for g, _ in rows}) > 1:
        n, sx, sy = len(rows), sum(g for g, _ in rows), sum(v for _, v in rows)
        sxx, sxy = sum(g * g for g, _ in rows), sum(g * v for g, v in rows)
        a = (n * sxy - sx * sy) / (n * sxx - sx * sx) if n * sxx != sx * sx else float("nan")
        print(f"  straight line through them: SteamVR ≈ {a:.3f} × gauge {(sy - a * sx) / n:+.2f}")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    {"record": record, "install": install, "uninstall": uninstall, "report": report}.get(
        cmd, lambda: sys.exit(__doc__))()
