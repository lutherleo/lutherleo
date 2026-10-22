#!/usr/bin/env python3
"""
Render the streak / numbers card from data/contributions.json as a
terminal-window SVG: six stat tiles slide in and count up to the real value,
then a contributions-per-month bar chart grows in underneath.

The count-up is a stack of pre-rendered frames toggled with SMIL <animate>, since
GitHub runs SMIL/CSS inside <img> SVGs but never JS. The count-up and the bars
replay every CYCLE seconds, so the card is never caught "finished and static"
by someone who scrolls down to it later.
Colours follow template2's Blueprint palette (slate + emerald + cyan).

    python scripts/render_stats_svg.py [data.json] [output.svg]
"""
import datetime
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "data", "contributions.json")
OUT = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, "..", "assets", "stats.svg")

BG = "#0B1220"
BG2 = "#0F172A"
TILE = "#111827"
FRAME = "#1E293B"
MUTED = "#64748B"
INK = "#E2E8F0"
ACCENT = "#10B981"
PEAK = "#34D399"
BAR = "#047857"
CYAN = "#06B6D4"

W, H = 860, 600
PAD = 18
TITLEBAR_H = 30
COLS, ROWS = 3, 2
GAP = 14
TILE_W = (W - PAD * 2 - GAP * (COLS - 1)) / COLS
TILE_H = 120
TILES_TOP = TITLEBAR_H + PAD
CHART_TOP = TILES_TOP + ROWS * TILE_H + (ROWS - 1) * GAP + GAP

# timing (seconds)
TILE_STAGGER = 0.15
SLIDE_DUR = 0.45
COUNT_DUR = 1.2
FRAMES = 16
BAR_START = TILE_STAGGER * COLS * ROWS + 0.4
BAR_STAGGER = 0.06
BAR_DUR = 0.6
CYCLE = 10          # count-up + bars replay on this loop
SHRINK = 0.4        # bars drop back down at the end of each loop


def pct(t):
    return f"{100 * t / CYCLE:.2f}%"


def short(d):
    d = datetime.date.fromisoformat(d)
    return f"{d:%b} {d.day}"  # no %-d: it isn't portable to Windows


def span(s):
    if not s["length"]:
        return "—"
    return short(s["start"]) if s["start"] == s["end"] else f'{short(s["start"])} – {short(s["end"])}'


def days_word(n):
    return " day" if n == 1 else " days"


def fmt(v, like):
    return f"{v:,.1f}" if isinstance(like, float) else f"{int(round(v)):,}"


data = json.load(open(SRC, encoding="utf-8"))
user = data["username"].lower()
cur, lng, best = data["current_streak"], data["longest_streak"], data["best_day"]
n_days = len(data["days"])

# (label, value, suffix, caption, accent)
tiles = [
    ("current streak", cur["length"], days_word(cur["length"]), span(cur), ACCENT),
    ("longest streak", lng["length"], days_word(lng["length"]), span(lng), INK),
    ("contributions", data["total_contributions"], "", "in the last year", INK),
    ("active days", data["active_days"], f" / {n_days}", f'{data["active_days"] / n_days:.0%} of the year', INK),
    ("best day", best["count"], "", short(best["date"]), CYAN),
    ("avg / active day", float(data["avg_per_active_day"]), "", "contributions", INK),
]

parts = [
    f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
    f'font-family="ui-monospace, SFMono-Regular, Menlo, Consolas, monospace">',
    '<style>'
    f'.t{{opacity:0;animation:in {SLIDE_DUR}s ease-out both}}'
    '@keyframes in{0%{opacity:0;transform:translateY(10px)}100%{opacity:1;transform:translateY(0)}}'
    f'.b{{transform-box:fill-box;transform-origin:bottom;transform:scaleY(0);animation:grow {CYCLE}s ease-out infinite both}}'
    f'@keyframes grow{{0%{{transform:scaleY(0)}}{pct(BAR_DUR)}{{transform:scaleY(1)}}'
    f'{pct(CYCLE - 1 - SHRINK)}{{transform:scaleY(1)}}{pct(CYCLE - 1)},100%{{transform:scaleY(0)}}}}'
    f'.pk{{opacity:0;animation:pk {CYCLE}s ease-out infinite both}}'
    f'@keyframes pk{{0%{{opacity:0}}{pct(0.3)}{{opacity:1}}{pct(CYCLE - 1 - BAR_DUR - SHRINK)}{{opacity:1}}'
    f'{pct(CYCLE - 1 - BAR_DUR)},100%{{opacity:0}}}}'
    '@media (prefers-reduced-motion: reduce){.t,.b,.pk{opacity:1!important;transform:none!important;animation:none!important}}'
    '</style>',
    f'<defs><linearGradient id="bg" x1="0" y1="0" x2="0" y2="1">'
    f'<stop offset="0" stop-color="{BG2}"/><stop offset="1" stop-color="{BG}"/></linearGradient></defs>',
    f'<rect width="{W}" height="{H}" rx="12" fill="url(#bg)"/>',
    f'<rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" rx="12" fill="none" stroke="{FRAME}"/>',
    f'<line x1="0" y1="{TITLEBAR_H}" x2="{W}" y2="{TITLEBAR_H}" stroke="{FRAME}"/>',
]
for i, dot in enumerate(["#ff5f56", "#ffbd2e", "#27c93f"]):
    parts.append(f'<circle cx="{PAD + i * 16}" cy="{TITLEBAR_H / 2}" r="5" fill="{dot}"/>')
parts.append(f'<text x="{W / 2}" y="{TITLEBAR_H / 2 + 4}" fill="{MUTED}" font-size="12" '
             f'text-anchor="middle">{user}@github: ~$ ./stats.sh</text>')

# ---- stat tiles ----------------------------------------------------------
for i, (label, value, suffix, caption, accent) in enumerate(tiles):
    col, row = i % COLS, i // COLS
    x = PAD + col * (TILE_W + GAP)
    y = TILES_TOP + row * (TILE_H + GAP)
    start = i * TILE_STAGGER
    count_start = start + SLIDE_DUR * 0.6

    parts.append(f'<g class="t" style="animation-delay:{start:.2f}s">')
    parts.append(f'<rect x="{x:.1f}" y="{y}" width="{TILE_W:.1f}" height="{TILE_H}" rx="10" '
                 f'fill="{TILE}" stroke="{FRAME}"/>')
    parts.append(f'<text x="{x + 18:.1f}" y="{y + 30}" fill="{MUTED}" font-size="14">'
                 f'<tspan fill="{ACCENT}">$</tspan> {label}</text>')

    # count-up frames: ease-out so it decelerates into the real number
    num_y = y + 76
    for k in range(1, FRAMES + 1):
        p = k / FRAMES
        v = value * (1 - (1 - p) ** 3)
        # each frame is visible for its slice of the count, then hidden for the
        # rest of the loop; the last frame holds until the loop restarts
        t_on = COUNT_DUR * (k - 1) / FRAMES / CYCLE
        t_off = COUNT_DUR * k / FRAMES / CYCLE
        if k == 1:
            values, times = "1;0", f"0;{t_off:.4f}"
        elif k < FRAMES:
            values, times = "0;1;0", f"0;{t_on:.4f};{t_off:.4f}"
        else:
            values, times = "0;1", f"0;{t_on:.4f}"
        anim = (f'<animate attributeName="opacity" values="{values}" keyTimes="{times}" calcMode="discrete" '
                f'dur="{CYCLE}s" begin="{count_start:.3f}s" repeatCount="indefinite"/>')
        parts.append(
            f'<text x="{x + 18:.1f}" y="{num_y}" opacity="0" font-size="38" font-weight="700" fill="{accent}">'
            f'{fmt(v, value)}<tspan font-size="16" font-weight="400" fill="{MUTED}">{suffix}</tspan>'
            f'{anim}</text>'
        )
    parts.append(f'<text x="{x + 18:.1f}" y="{y + 102}" fill="{MUTED}" font-size="13">{caption}</text>')
    parts.append('</g>')

# ---- monthly bars --------------------------------------------------------
monthly = data["monthly"]
chart_x, chart_w = PAD, W - PAD * 2
chart_h = H - PAD - CHART_TOP
parts.append(f'<g class="t" style="animation-delay:{BAR_START - 0.3:.2f}s">')
parts.append(f'<rect x="{chart_x}" y="{CHART_TOP}" width="{chart_w}" height="{chart_h}" rx="10" '
             f'fill="{TILE}" stroke="{FRAME}"/>')
parts.append(f'<text x="{chart_x + 18}" y="{CHART_TOP + 30}" fill="{MUTED}" font-size="14">'
             f'<tspan fill="{ACCENT}">$</tspan> contributions / month</text>')
parts.append('</g>')

plot_top = CHART_TOP + 62
plot_bot = CHART_TOP + chart_h - 34
plot_l, plot_r = chart_x + 18, chart_x + chart_w - 18
slot = (plot_r - plot_l) / len(monthly)
bar_w = slot * 0.62
peak = max(m["total"] for m in monthly) or 1
for i, m in enumerate(monthly):
    h = max(2, (plot_bot - plot_top) * m["total"] / peak)
    bx = plot_l + i * slot + (slot - bar_w) / 2
    is_peak = m["total"] == peak
    delay = BAR_START + i * BAR_STAGGER
    parts.append(f'<rect class="b" x="{bx:.1f}" y="{plot_bot - h:.1f}" width="{bar_w:.1f}" height="{h:.1f}" '
                 f'rx="3" fill="{PEAK if is_peak else BAR}" style="animation-delay:{delay:.2f}s">'
                 f'<title>{m["month"]}: {m["total"]:,}</title></rect>')
    mon = datetime.date.fromisoformat(m["month"] + "-01").strftime("%b")
    parts.append(f'<text x="{bx + bar_w / 2:.1f}" y="{plot_bot + 22}" fill="{MUTED}" font-size="12" '
                 f'text-anchor="middle">{mon}</text>')
    if is_peak:
        parts.append(f'<text class="pk" style="animation-delay:{delay + BAR_DUR:.2f}s" x="{bx + bar_w / 2:.1f}" '
                     f'y="{plot_bot - h - 8:.1f}" fill="{INK}" font-size="13" font-weight="700" '
                     f'text-anchor="middle">{peak:,}</text>')

parts.append('</svg>')
svg = "".join(parts)
os.makedirs(os.path.dirname(os.path.abspath(OUT)), exist_ok=True)
open(OUT, "w", encoding="utf-8").write(svg)
print(f"wrote {OUT}: {W} x {H}, {len(svg) // 1024} KB")
