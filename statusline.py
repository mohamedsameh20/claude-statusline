#!/usr/bin/env python3
"""Claude Code status line.

Reads the session JSON from stdin and the terminal width from $COLUMNS, which
Claude Code sets before each run. No network, no subprocesses, no files.

  ✻ Opus 5.5  high ●●●○○       │  5h ▰▰▰▱▱▱▱▱▱▱  34% ↻ 2h10m 16:40     │  ● cache 91% 42m  ·  $0.42  ·  +156 −23
  ctx ▰▱▱▱▱▱▱▱▱▱  10% 99k/1.0M │  7d ▰▰▰▰▰▰▰▰▱▱  81% ↻ 3d4h Sun 07:00  │  ~/project  ⎇ wt  ◇ agent

Everything sits on the left in a two-row grid whose dividers line up.
"""
import json
import math
import os
import re
import sys
import time


def rgb(r, g, b):
    return f"\033[38;2;{r};{g};{b}m"


RESET = "\033[0m"
BOLD = "\033[1m"

SAGE_RGB = (143, 188, 150)
AMBER_RGB = (232, 182, 96)
CORAL_RGB = (226, 104, 92)
TRACK_RGB = (52, 49, 45)     # empty part of a bar

CLAUDE = rgb(217, 119, 87)   # Claude terracotta
CREAM = rgb(236, 230, 218)
MUTED = rgb(150, 143, 132)
FAINT = rgb(86, 82, 76)
OK = rgb(*SAGE_RGB)
WARN = rgb(*AMBER_RGB)
HOT = rgb(*CORAL_RGB)

# Bars run sage -> amber -> coral along their length, so a filling bar heats up.
GRADIENT = ((0.0, SAGE_RGB), (0.5, AMBER_RGB), (1.0, CORAL_RGB))

# Alerts breathe: the colour fades between bright and dim on a slow cycle.
# Each run renders one frame from the clock; refreshInterval sets the frame rate.
ALERT_PCT = 90
CACHE_ALERT_SECS = 300
PULSE_PERIOD = 4

SEP = f"  {FAINT}·{RESET}  "
COL_SEP = f"  {FAINT}│{RESET}  "
BAR_WIDTH = 10
EFFORT_LEVELS = ("low", "medium", "high", "xhigh", "max")
DIR_MAX = 28
# Claude Code indents the status line; leave room so rows never wrap.
EDGE_MARGIN = 4
ANSI = re.compile(r"\033\[[0-9;]*m")


def num(value):
    """Float from a JSON value, or None for null / missing / junk."""
    if isinstance(value, bool):
        return None
    try:
        n = float(value)
    except (TypeError, ValueError):
        return None
    return n if math.isfinite(n) else None


def get(data, *keys):
    for key in keys:
        if not isinstance(data, dict):
            return None
        data = data.get(key)
    return data


def text(value):
    return value if isinstance(value, str) and value else None


def visible(s):
    return len(ANSI.sub("", s))


def tone(pct):
    if pct >= 80:
        return HOT
    if pct >= 50:
        return WARN
    return OK


def mix(a, b, t):
    return tuple(round(x + (y - x) * t) for x, y in zip(a, b))


def gradient(pos):
    for (p0, c0), (p1, c1) in zip(GRADIENT, GRADIENT[1:]):
        if pos <= p1:
            return mix(c0, c1, (pos - p0) / (p1 - p0))
    return GRADIENT[-1][1]


def pulse(colour):
    """This frame's shade of a breathing colour."""
    phase = 0.5 + 0.5 * math.sin(2 * math.pi * time.time() / PULSE_PERIOD)
    return rgb(*mix(mix(colour, TRACK_RGB, 0.6), colour, phase))


def bar(pct, width):
    """Thin gradient bar in half-cell steps over a dim track."""
    if not width:
        return ""
    halves = int(pct / 100 * width * 2 + 0.5)
    track = rgb(*TRACK_RGB)
    cells = []
    for i in range(width):
        fill = max(0, min(2, halves - i * 2))
        colour = rgb(*gradient((i + 0.5) / width))
        cells.append(f"{colour}━" if fill == 2 else f"{colour}╸" if fill else f"{track}━")
    return "".join(cells) + f"{RESET} "


def tokens(n):
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.0f}k"
    return f"{n:.0f}"


def countdown(reset_at):
    mins = math.ceil((reset_at - time.time()) / 60)
    if mins <= 0:
        return "now"
    days, mins = divmod(mins, 1440)
    hours, mins = divmod(mins, 60)
    if days:
        return f"{days}d{hours}h"
    if hours:
        return f"{hours}h{mins:02d}m"
    return f"{mins}m"


def clock(reset_at):
    t = time.localtime(reset_at)
    if reset_at - time.time() >= 86400:
        return time.strftime("%a %H:%M", t)
    return time.strftime("%H:%M", t)


def meter(label, pct, bar_width, extra="", breathe=True):
    # Fixed-width percentage so the segments don't shift as values change.
    pct = max(0.0, min(100.0, pct))
    colour = tone(pct)
    label_colour = MUTED
    if breathe and pct >= ALERT_PCT:
        colour = label_colour = pulse(CORAL_RGB)
    return (
        f"{label_colour}{label}{RESET} {bar(pct, bar_width)}"
        f"{BOLD}{colour}{int(pct + 0.5):>3}%{RESET}{extra}"
    )


# Where you are.

def directory(data):
    cwd = text(get(data, "workspace", "current_dir")) or text(get(data, "cwd")) or os.getcwd()
    home = os.path.expanduser("~")
    if cwd == home or cwd.startswith(home + os.sep):
        cwd = "~" + cwd[len(home):]
    if len(cwd) > DIR_MAX:
        # Keep the tail, which is the part that tells projects apart.
        cwd = "…" + cwd[-(DIR_MAX - 1):]
    out = f"{CREAM}{cwd}{RESET}"
    worktree = text(get(data, "workspace", "git_worktree"))
    if worktree:
        out += f"  {MUTED}⎇ {worktree}{RESET}"
    return out


# Who is answering.

def agent(data):
    name = text(get(data, "agent", "name"))
    return f"{MUTED}◇ {name}{RESET}" if name else None


def model(data):
    name = text(get(data, "model", "display_name")) or text(get(data, "model", "id"))
    if not name:
        return None
    return f"{CLAUDE}✻{RESET} {BOLD}{CLAUDE}{name}{RESET}"


def effort(data):
    level = text(get(data, "effort", "level"))
    if not level:
        return None
    if level not in EFFORT_LEVELS:
        return f"{MUTED}{level}{RESET}"
    rank = EFFORT_LEVELS.index(level) + 1
    dots = f"{CLAUDE}{'●' * rank}{FAINT}{'○' * (len(EFFORT_LEVELS) - rank)}{RESET}"
    return f"{MUTED}{level}{RESET} {dots}"


# How much room is left.

def context(data, bar_width):
    used = num(get(data, "context_window", "total_input_tokens"))
    size = num(get(data, "context_window", "context_window_size"))
    pct = num(get(data, "context_window", "used_percentage"))
    if pct is None and used is not None and size:
        pct = used / size * 100
    if pct is None and used is None:
        return f"{MUTED}ctx{RESET} {bar(0, bar_width)}{FAINT}   —{RESET}"
    extra = f" {MUTED}{tokens(used or 0)}{FAINT}/{tokens(size)}{RESET}" if size else ""
    return meter("ctx", pct or 0, bar_width, extra)


def limit(data, label, key, bar_width, show_clock):
    window = get(data, "rate_limits", key)
    pct = num(get(window, "used_percentage"))
    if pct is None:
        return None
    extra = ""
    reset_at = num(get(window, "resets_at"))
    if reset_at is not None:
        extra = f" {MUTED}↻ {countdown(reset_at)}{RESET}"
        if show_clock:
            extra += f" {FAINT}{clock(reset_at)}{RESET}"
    # The weekly window moves too slowly for an animated alert to help.
    return meter(label, pct, bar_width, extra, breathe=key != "seven_day")


# Full, compact, minimal: the first that fits the terminal wins.
METER_STYLES = ((BAR_WIDTH, True), (5, False), (0, False))


# Session stats.

def cache(data):
    warm = get(data, "prompt_cache", "warm")
    if not isinstance(warm, bool):
        return None
    if not warm:
        return f"{HOT}○{RESET} {MUTED}cache cold{RESET}"
    expires_at = num(get(data, "prompt_cache", "expires_at"))
    expiring = expires_at is not None and expires_at - time.time() <= CACHE_ALERT_SECS
    dot = pulse(AMBER_RGB) if expiring else OK
    out = f"{dot}●{RESET} {MUTED}cache{RESET}"
    ratio = num(get(data, "prompt_cache", "hit_ratio"))
    if ratio is not None:
        out += f" {CREAM}{int(ratio * 100 + 0.5)}%{RESET}"
    if expires_at is not None:
        left = dot if expiring else FAINT
        out += f" {left}{countdown(expires_at)}{RESET}"
    return out


def cost(data):
    usd = num(get(data, "cost", "total_cost_usd"))
    return f"{CREAM}${usd:.2f}{RESET}" if usd is not None else None


def lines(data):
    added = num(get(data, "cost", "total_lines_added"))
    removed = num(get(data, "cost", "total_lines_removed"))
    if not added and not removed:
        return None
    return f"{OK}+{added or 0:.0f}{RESET} {HOT}−{removed or 0:.0f}{RESET}"


# Layout.

def group(*segments):
    return SEP.join(s for s in segments if s)


def terminal_width():
    try:
        cols = int(os.environ.get("COLUMNS", ""))
    except ValueError:
        return None
    return cols - EDGE_MARGIN if cols > EDGE_MARGIN else None


def grid(rows):
    """Pad cells so each column's divider lines up across rows."""
    columns = max(len(r) for r in rows)
    widths = [
        max((visible(r[i]) for r in rows if i < len(r) and r[i]), default=0)
        for i in range(columns)
    ]
    # Drop columns that are empty in every row.
    keep = [i for i in range(columns) if widths[i]]
    widths = [widths[i] for i in keep]
    rows = [[r[i] if i < len(r) else None for i in keep] for r in rows]
    out = []
    for cells in rows:
        cells = list(cells)
        while cells and not cells[-1]:
            cells.pop()
        padded = [
            (c or "") + " " * (widths[i] - visible(c or "")) for i, c in enumerate(cells)
        ]
        if padded:
            padded[-1] = cells[-1]  # no trailing padding on the last cell
        out.append(COL_SEP.join(padded))
    return out


def main():
    try:
        data = json.load(sys.stdin)
    except ValueError:
        data = {}
    if not isinstance(data, dict):
        data = {}

    identity = "  ".join(s for s in (model(data), effort(data)) if s)
    place = "  ".join(s for s in (directory(data), agent(data)) if s)
    session = group(cache(data), cost(data), lines(data))

    width = terminal_width()
    for bar_width, show_clock in METER_STYLES:
        five = limit(data, "5h", "five_hour", bar_width, show_clock)
        seven = limit(data, "7d", "seven_day", bar_width, show_clock)
        ctx = context(data, bar_width)
        # Meters stack in the first two columns; session and place sit beside
        # them, or drop below when the terminal is too narrow.
        layouts = [grid([[identity, five, session], [ctx, seven, place]])]
        extra = [s for s in (session, place) if s]
        if extra:
            layouts.append(grid([[identity, five], [ctx, seven]]) + extra)
        out = next(
            (lines for lines in layouts
             if width is None or max(visible(line) for line in lines) <= width),
            None,
        )
        if out:
            break
    else:
        out = layouts[-1]
    sys.stdout.write("\n".join(out))


if __name__ == "__main__":
    main()
