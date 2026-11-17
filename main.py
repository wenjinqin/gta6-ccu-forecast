"""GTA VI launch-day Twitch viewers forecaster (gta6-twitch-ccu-forecast-01).

Model: an empirical launch-curve forecaster. Every case file carries the full
hourly history of ~40 comparable game launches. For each comparable, this
program builds the launch day's log-ratio curve, log(viewers_h / viewers_1)
for hours 1..24, bridging gaps by log-linear interpolation. The forecast for
a new launch is, hour by hour, the weighted empirical quantiles of those
curves across the comparable set:

  - comparables whose unlock pattern matches the target's (rolling midnight
    local vs a single global unlock, read from the case notes and each
    comparable's unlock text) weigh 1.0, the rest 0.3;
  - the five scored quantile levels are read off the weighted distribution
    of log-ratios, then the spread around the median is scaled by 0.4 (a
    calibration fitted on the four practice launches: the raw cross-title
    dispersion proved far wider than any single launch's own outcome
    spread, and a grid over the scale bottomed out in a shallow basin
    around 0.35-0.45, so the middle of the basin is used);
  - each level's curve is smoothed over a 3-hour window before use, and the
    five quantiles of every hour are sorted so each row is non-decreasing.

The forecast is hour 1's print times exp(curve), rounded half up to 2
decimals. The program is deterministic: same case in, same forecast out.

Runs as the grader runs it: python3 -P -s /bot/main.py, standard library
only, no network. Outside the grader, MAKEFUN_INPUT_DIR and
MAKEFUN_OUTPUT_DIR stand in for /input and /output.
"""

import json
import math
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

INPUT_DIR = Path(os.environ.get("MAKEFUN_INPUT_DIR", "/input"))
OUTPUT_DIR = Path(os.environ.get("MAKEFUN_OUTPUT_DIR", "/output"))

LEVELS = [0.05, 0.25, 0.5, 0.75, 0.95]
W_SAME_CLASS = 1.0
W_OTHER_CLASS = 0.3
SPREAD_SCALE = 0.4
SMOOTH_RADIUS = 1
MIN_DAY_HOURS = 14


def unlock_class(text):
    """'rolling' for midnight-local rolling unlocks, 'global' for a single
    simultaneous unlock, 'other' when the text does not say."""
    t = (text or "").lower()
    if "midnight local" in t or "rolling midnight" in t or "midnight for all" in t:
        return "rolling"
    if "global unlock" in t or "simultaneous" in t or "single global" in t:
        return "global"
    return "other"


def day_hours(comp):
    """hour (1..24) -> viewers on the comparable's release day."""
    d0 = datetime.strptime(comp["day_start"][:10], "%Y-%m-%d")
    out = {}
    for pt in comp["hourly"]:
        t = datetime.strptime(pt["from"][:13], "%Y-%m-%dT%H")
        delta = (t - d0).total_seconds() / 3600
        if 0 <= delta < 24 and pt.get("viewers") and pt["viewers"] > 0:
            out[int(delta) + 1] = pt["viewers"]
    return out


def ratio_curve(hours):
    """log(viewers_h / viewers_1) for h = 1..24, gaps log-linearly bridged.
    None when the comparable's day is too sparse to trust."""
    if 1 not in hours or len(hours) < MIN_DAY_HOURS:
        return None
    base = math.log(hours[1])
    pts = {h: math.log(v) - base for h, v in hours.items()}
    known = sorted(pts)
    curve = {}
    for h in range(1, 25):
        if h in pts:
            curve[h] = pts[h]
            continue
        lo = max([x for x in known if x < h], default=None)
        hi = min([x for x in known if x > h], default=None)
        if lo is None:
            curve[h] = pts[hi]
        elif hi is None:
            curve[h] = pts[lo]
        else:
            curve[h] = pts[lo] + (pts[hi] - pts[lo]) * (h - lo) / (hi - lo)
    return curve


def weighted_quantile(pairs, tau):
    """Weighted quantile of (value, weight) pairs, linear on cumulative weight."""
    pairs = sorted(pairs)
    total = sum(w for _, w in pairs)
    if total <= 0:
        return pairs[len(pairs) // 2][0]
    target = tau * total
    acc = 0.0
    for i, (v, w) in enumerate(pairs):
        acc += w
        if acc >= target:
            if i == 0:
                return v
            prev_v = pairs[i - 1][0]
            frac = (target - (acc - w)) / w if w > 0 else 0.0
            return prev_v + frac * (v - prev_v)
    return pairs[-1][0]


def smooth(values, radius):
    if radius <= 0:
        return values
    out = []
    for i in range(len(values)):
        window = values[max(0, i - radius): i + radius + 1]
        out.append(sum(window) / len(window))
    return out


def round2(x):
    """Round half up to 2 decimals; whole numbers come back as int."""
    scaled = x * 100
    whole = math.floor(scaled)
    if scaled - whole >= 0.5:
        whole += 1
    v = whole / 100
    return int(v) if v == int(v) else v


def forecast_case(case):
    p1 = max(1.0, float(case["known"][0]["viewers"]))
    target_class = unlock_class(case.get("notes", ""))
    pool = []
    for comp in case.get("comparables", []):
        curve = ratio_curve(day_hours(comp))
        if curve is None:
            continue
        w = W_SAME_CLASS if unlock_class(comp.get("unlock", "")) == target_class else W_OTHER_CLASS
        pool.append((curve, w))
    if not pool:
        # No usable comparables: fall back to a flat day at hour 1's level.
        return {"hours": [{"hour": h, "q": [round2(p1)] * 5} for h in range(2, 25)]}
    raw = {tau: [] for tau in LEVELS}
    for h in range(2, 25):
        for tau in LEVELS:
            raw[tau].append(weighted_quantile([(c[h], w) for c, w in pool], tau))
    for tau in LEVELS:
        raw[tau] = smooth(raw[tau], SMOOTH_RADIUS)
    rows = []
    for i, h in enumerate(range(2, 25)):
        med = raw[0.5][i]
        qs = [p1 * math.exp(med + SPREAD_SCALE * (raw[tau][i] - med)) for tau in LEVELS]
        qs = sorted(max(0.01, q) for q in qs)
        rows.append({"hour": h, "q": [round2(q) for q in qs]})
    return {"hours": rows}


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for path in sorted(INPUT_DIR.glob("*.in")):
        case = json.loads(path.read_text())
        result = forecast_case(case)
        out_path = OUTPUT_DIR / (path.stem + ".out")
        out_path.write_text(json.dumps(result, separators=(",", ":")) + "\n")


if __name__ == "__main__":
    main()
