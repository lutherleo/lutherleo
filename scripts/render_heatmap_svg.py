#!/usr/bin/env python3
"""
Render data/contributions.json as an animated contribution graph: cells pop in
week by week with a brief flash, the yearly total appears underneath, the graph
holds, then sweeps out and replays every CYCLE seconds -- so it is never caught
"finished and static" by someone who scrolls down to it later.
GitHub runs CSS animations inside <img> SVGs (never JS), so it is pure CSS.

Colours follow template2's Blueprint palette (slate + emerald).

    python scripts/render_heatmap_svg.py [data.json] [output.svg]
"""
import datetime
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "data", "contributions.json")
OUT = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, "..", "assets", "contrib-heatmap.svg")

LEVELS = ["#1E293B", "#064E3B", "#047857", "#10B981", "#34D399"]
MUTED = "#64748B"
INK = "#A7F3D0"
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

CELL, GAP, RAD, LEFT, TOP = 13, 3, 2.5, 34, 24
REVEAL, DUR = 3.6, 0.55  # seconds: whole sweep, single cell
CYCLE = 12               # seconds per loop (reveal + hold + sweep out)
OUT_AT, OUT_DUR = CYCLE - 1.0, 0.4  # per cell, relative to its own start


def pct(t):
    return f"{100 * t / CYCLE:.2f}%"


data = json.load(open(SRC, encoding="utf-8"))
days = data["days"]
first = datetime.date.fromisoformat(days[0]["date"])
week0 = first - datetime.timedelta(days=(first.weekday() + 1) % 7)  # Sunday on/before first day


def pos(d):
    off = (datetime.date.fromisoformat(d["date"]) - week0).days
    return off // 7, off % 7


n_weeks = pos(days[-1])[0] + 1
W = LEFT + n_weeks * (CELL + GAP) + 6
H = TOP + 7 * (CELL + GAP) + 22
max_order = (n_weeks - 1) + 6 * 0.55

labels, last_m = [], None
for wk in range(n_weeks):
    d = week0 + datetime.timedelta(days=wk * 7 + 6)  # label a week by its Saturday
    if d.month != last_m and wk < n_weeks - 1:
        last_m = d.month
        labels.append(f'<text class="lbl" x="{LEFT + wk * (CELL + GAP)}" y="{TOP - 8}">{MONTHS[d.month - 1]}</text>')
for name, r in [("Mon", 1), ("Wed", 3), ("Fri", 5)]:
    labels.append(f'<text class="lbl" x="2" y="{TOP + r * (CELL + GAP) + CELL - 2}">{name}</text>')

rects = []
for d in days:
    wk, row = pos(d)
    lvl = max(0, min(4, d["level"]))
    delay = round((wk + row * 0.55) / max_order * REVEAL, 3)
    cls = "c g" if lvl else "c"
    tip = f'{d["count"]} contribution{"" if d["count"] == 1 else "s"} on {d["date"]}'
    rects.append(
        f'<rect class="{cls}" x="{LEFT + wk * (CELL + GAP)}" y="{TOP + row * (CELL + GAP)}" '
        f'width="{CELL}" height="{CELL}" rx="{RAD}" fill="{LEVELS[lvl]}" '
        f'style="animation-delay:{delay}s"><title>{tip}</title></rect>'
    )

total = data["total_contributions"]
svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="-apple-system,Segoe UI,Helvetica,Arial,sans-serif">
<style>
  text.lbl {{ fill:{MUTED}; font-size:13px; font-weight:600; }}
  text.total {{ fill:{INK}; font-size:15px; font-weight:700; opacity:0; animation:fade {CYCLE}s ease-out infinite both; }}
  .c {{ transform-box:fill-box; transform-origin:center; opacity:0; animation:pop {CYCLE}s ease-out infinite both; }}
  .g {{ animation:pop {CYCLE}s ease-out infinite both, flash {CYCLE}s ease-out infinite both; }}
  @keyframes pop {{ 0%{{opacity:0;transform:scale(.2)}} {pct(DUR * 0.6)}{{opacity:1;transform:scale(1.1)}} {pct(DUR)}{{opacity:1;transform:scale(1)}}
    {pct(OUT_AT)}{{opacity:1;transform:scale(1)}} {pct(OUT_AT + OUT_DUR)},100%{{opacity:0;transform:scale(.2)}} }}
  @keyframes flash {{ 0%,{pct((DUR + 0.15) * 0.45)}{{filter:brightness(2.2)}} {pct(DUR + 0.15)},100%{{filter:brightness(1)}} }}
  @keyframes fade {{ 0%,{pct(REVEAL)}{{opacity:0}} {pct(REVEAL + 0.6)},{pct(OUT_AT)}{{opacity:1}} {pct(OUT_AT + OUT_DUR)},100%{{opacity:0}} }}
  @media (prefers-reduced-motion: reduce) {{ .c, text.total {{ opacity:1 !important; animation:none !important; }} }}
</style>
{"".join(labels)}
{"".join(rects)}
<text class="total" x="{LEFT}" y="{H - 6}">{total:,} contributions in the last year</text>
</svg>'''

os.makedirs(os.path.dirname(os.path.abspath(OUT)), exist_ok=True)
open(OUT, "w", encoding="utf-8").write(svg)
print(f"wrote {OUT}: {len(days)} days, {total:,} contributions, {len(svg) // 1024} KB")
