#!/usr/bin/env python3
"""
Nightly plate.

Public GitHub activity for harishstacks, drawn as a cyanotype meridian —
not a dashboard, not a studio wall. Same date + stats → same plate.
inspect.svg is the filing copy.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import random
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
USER = os.environ.get("GITHUB_REPOSITORY_OWNER") or os.environ.get("STUDIO_USER") or "harishstacks"
TOKEN = os.environ.get("GITHUB_TOKEN", "")

W, H = 1200, 720
# Cyanotype: Prussian field, bleach highlights, one survey flag.
VOID = "#04101c"
FIELD = "#0a3a68"
FIELD_LIFT = "#15608a"
BLEACH = "#d7f2ea"
BLEACH_DIM = "#8ec4c0"
INK = "#062033"
FLAG = "#ff5a32"
CAPTION = "#6aa0a8"
MONO = "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace"
SANS = "ui-sans-serif, system-ui, 'Segoe UI', sans-serif"

PLATES = [
    {"id": "agro", "n": "01", "title": "AGRO", "note": "CROP · STORE"},
    {"id": "weather", "n": "02", "title": "WEATHER", "note": "PAST → NEXT"},
    {"id": "churn", "n": "03", "title": "CHURN", "note": "WHO LEAVES"},
]


@dataclass
class StrokeEvent:
    hour: int
    repo: str
    dow: int
    weight: int = 1


@dataclass
class StudioData:
    generated: datetime
    seed: str
    commits_week: int
    currently: str
    events: list[StrokeEvent] = field(default_factory=list)
    from_api: bool = False


def esc(text: str) -> str:
    amp, lt, gt, quot = chr(38), chr(60), chr(62), chr(34)
    return (
        (text or "")
        .replace(amp, amp + "amp;")
        .replace(lt, amp + "lt;")
        .replace(gt, amp + "gt;")
        .replace(quot, amp + "quot;")
    )


def gh_get(url: str) -> Any:
    headers = {
        "User-Agent": "harishstacks-nightly-studio",
        "Accept": "application/vnd.github+json",
    }
    if TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())


def fetch_activity(now: datetime) -> StudioData:
    week_ago = now - timedelta(days=7)
    events: list[StrokeEvent] = []
    currently = "—"
    try:
        repos = gh_get(f"https://api.github.com/users/{USER}/repos?per_page=100&sort=pushed")
        for r in repos:
            name = r.get("name") or ""
            if name and name.lower() != USER.lower():
                currently = name
                break
        page = 1
        while page <= 3:
            batch = gh_get(
                f"https://api.github.com/users/{USER}/events/public?per_page=100&page={page}"
            )
            if not batch:
                break
            for ev in batch:
                created = datetime.fromisoformat(ev["created_at"].replace("Z", "+00:00"))
                if created < week_ago:
                    continue
                repo = (ev.get("repo") or {}).get("name", "").split("/")[-1] or "studio"
                hour = created.hour
                dow = created.weekday()
                if ev.get("type") == "PushEvent":
                    n = len((ev.get("payload") or {}).get("commits") or []) or 1
                    events.append(StrokeEvent(hour=hour, repo=repo, dow=dow, weight=n))
                elif ev.get("type") in {"CreateEvent", "PullRequestEvent", "IssuesEvent"}:
                    events.append(StrokeEvent(hour=hour, repo=repo, dow=dow, weight=1))
            if len(batch) < 100:
                break
            page += 1
        commits_week = sum(e.weight for e in events)
        seed = _seed(now, commits_week, currently)
        return StudioData(
            generated=now,
            seed=seed,
            commits_week=commits_week,
            currently=currently,
            events=events,
            from_api=True,
        )
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, ValueError, KeyError):
        return fallback_activity(now)


def _seed(now: datetime, commits_week: int, currently: str) -> str:
    day = now.astimezone(timezone.utc).date().isoformat()
    raw = f"{day}|{commits_week}|{currently}|{USER}"
    return hashlib.sha256(raw.encode()).hexdigest()[:8]


def fallback_activity(now: datetime) -> StudioData:
    day = now.astimezone(timezone.utc).date().isoformat()
    seed = hashlib.sha256(f"{day}|fallback|{USER}".encode()).hexdigest()[:8]
    rng = random.Random(int(seed, 16))
    repos = ["Agro-Genix", "Customer-Churn-prediction", "harishstacks", "IPL--auction"]
    n = rng.randint(3, 11)
    events = []
    for _ in range(n):
        events.append(
            StrokeEvent(
                hour=rng.choice([9, 10, 11, 14, 15, 16, 21, 22, 23]),
                repo=rng.choice(repos),
                dow=rng.randint(0, 6),
                weight=rng.choice([1, 1, 1, 2]),
            )
        )
    currently = rng.choice(repos)
    commits_week = sum(e.weight for e in events)
    seed = _seed(now, commits_week, currently)
    return StudioData(
        generated=now,
        seed=seed,
        commits_week=commits_week,
        currently=currently,
        events=events,
        from_api=False,
    )


def pigment_for(repo: str) -> str:
    h = int(hashlib.sha256(repo.encode()).hexdigest()[:4], 16)
    return (BLEACH, BLEACH_DIM, FLAG)[h % 3]


def polar(cx: float, cy: float, r: float, theta: float) -> tuple[float, float]:
    return cx + r * math.cos(theta), cy + r * math.sin(theta)


def hour_theta(hour: float) -> float:
    return -math.pi / 2 + (hour / 24) * math.tau


# --- Constructed wordmark (photogram cutouts; no webfonts) --------------------

def _bar(x: float, y: float, w: float, h: float) -> str:
    return f"M {x:.1f},{y:.1f} h {w:.1f} v {h:.1f} h {-w:.1f} z"


def _h(x: float, y: float, w: float, h: float, t: float) -> str:
    return _bar(x, y, t, h) + _bar(x + w - t, y, t, h) + _bar(x, y + h * 0.46, w, t)


def _a(x: float, y: float, w: float, h: float, t: float) -> str:
    peak = x + w / 2
    left = (
        f"M {x:.1f},{y + h:.1f} L {peak - t * 0.35:.1f},{y:.1f} "
        f"L {peak + t * 0.55:.1f},{y:.1f} L {x + t * 1.15:.1f},{y + h:.1f} z"
    )
    right = (
        f"M {x + w:.1f},{y + h:.1f} L {peak + t * 0.35:.1f},{y:.1f} "
        f"L {peak - t * 0.55:.1f},{y:.1f} L {x + w - t * 1.15:.1f},{y + h:.1f} z"
    )
    return left + right + _bar(x + w * 0.22, y + h * 0.56, w * 0.56, t)


def _r(x: float, y: float, w: float, h: float, t: float) -> str:
    stem = _bar(x, y, t, h)
    bowl = (
        f"M {x:.1f},{y:.1f} h {w * 0.58:.1f} "
        f"q {w * 0.42:.1f},0 {w * 0.42:.1f},{h * 0.26:.1f} "
        f"q 0,{h * 0.26:.1f} {-w * 0.42:.1f},{h * 0.26:.1f} "
        f"H {x:.1f} z"
    )
    # Open the bowl with a counter that does not cut the stem.
    counter = (
        f"M {x + t:.1f},{y + t:.1f} H {x + w * 0.52:.1f} "
        f"q {w * 0.2:.1f},0 {w * 0.2:.1f},{h * 0.16:.1f} "
        f"q 0,{h * 0.16:.1f} {-w * 0.2:.1f},{h * 0.16:.1f} "
        f"H {x + t:.1f} z"
    )
    leg = (
        f"M {x + w * 0.42:.1f},{y + h * 0.5:.1f} L {x + w:.1f},{y + h:.1f} "
        f"L {x + w - t * 1.1:.1f},{y + h:.1f} L {x + w * 0.28:.1f},{y + h * 0.5:.1f} z"
    )
    return (
        f'<path d="{stem}{leg}" fill="{BLEACH}"/>'
        f'<path d="{bowl}{counter}" fill="{BLEACH}" fill-rule="evenodd"/>'
    )


def _i(x: float, y: float, w: float, h: float, t: float) -> str:
    g = (w - t) / 2
    return _bar(x + g, y, t, h)


def _s(x: float, y: float, w: float, h: float, t: float) -> str:
    # Instrument S: five bars, like a split-flap stencil.
    return (
        _bar(x, y, w, t)
        + _bar(x, y, t, h * 0.42)
        + _bar(x, y + h * 0.46 - t / 2, w, t)
        + _bar(x + w - t, y + h * 0.46, t, h * 0.54)
        + _bar(x, y + h - t, w, t)
    )


def wordmark(x: float, y: float, letter_h: float, letters: str = "HARISH") -> str:
    unit = letter_h * 0.36
    t = letter_h * 0.12
    gap = letter_h * 0.06
    widths = {"H": unit, "A": unit * 1.08, "R": unit, "I": unit * 0.4, "S": unit}
    drawers = {"H": _h, "A": _a, "R": _r, "I": _i, "S": _s}
    parts: list[str] = []
    cx = x
    for ch in letters:
        w = widths[ch]
        d = drawers[ch](cx, y, w, letter_h, t)
        if d.strip().startswith("<"):
            parts.append(d)
        else:
            parts.append(f'<path d="{d}" fill="{BLEACH}"/>')
        cx += w + gap
    return "".join(parts)


def wordmark_stack(x: float, y: float, letter_h: float) -> str:
    """Two-line photogram: HAR / ISH — full name, poster scale."""
    gap_y = letter_h * 0.08
    return wordmark(x, y, letter_h, "HAR") + wordmark(
        x + letter_h * 0.1, y + letter_h + gap_y, letter_h, "ISH"
    )


def crop_marks() -> str:
    marks = []
    for x, y, dx, dy in (
        (18, 18, 22, 0),
        (18, 18, 0, 22),
        (W - 18, 18, -22, 0),
        (W - 18, 18, 0, 22),
        (18, H - 18, 22, 0),
        (18, H - 18, 0, -22),
        (W - 18, H - 18, -22, 0),
        (W - 18, H - 18, 0, -22),
    ):
        marks.append(
            f'<line x1="{x}" y1="{y}" x2="{x + dx}" y2="{y + dy}" '
            f'stroke="{BLEACH}" stroke-width="0.8" opacity="0.45"/>'
        )
    return "\n".join(marks)


def meridian_grid(cx: float, cy: float, r_max: float) -> str:
    parts: list[str] = []
    for i in range(1, 8):
        r = 36 + i * (r_max - 36) / 7
        op = 0.12 if i < 7 else 0.28
        parts.append(
            f'<circle cx="{cx}" cy="{cy}" r="{r:.1f}" fill="none" '
            f'stroke="{BLEACH}" stroke-width="0.7" opacity="{op}"/>'
        )
    for hour in range(24):
        th = hour_theta(hour)
        inner, outer = 28, r_max
        x1, y1 = polar(cx, cy, inner, th)
        x2, y2 = polar(cx, cy, outer, th)
        major = hour % 6 == 0
        parts.append(
            f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
            f'stroke="{BLEACH}" stroke-width="{1.1 if major else 0.45}" '
            f'opacity="{0.28 if major else 0.08}"/>'
        )
        if major:
            lx, ly = polar(cx, cy, r_max + 16, th)
            label = f"{hour:02d}"
            parts.append(
                f'<text x="{lx:.1f}" y="{ly:.1f}" text-anchor="middle" dominant-baseline="middle" '
                f'font-family="{MONO}" font-size="9" fill="{BLEACH_DIM}">{label}</text>'
            )
    # Day rings read outward: Mon nearest the hub.
    for i, label in enumerate(("MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN")):
        r = 36 + (i + 0.5) * (r_max - 36) / 7
        tx, ty = polar(cx, cy, r, hour_theta(7.5))
        parts.append(
            f'<text x="{tx:.1f}" y="{ty:.1f}" font-family="{MONO}" font-size="7" '
            f'fill="{CAPTION}" opacity="0.55" text-anchor="middle">{label}</text>'
        )
    parts.append(
        f'<circle cx="{cx}" cy="{cy}" r="6" fill="none" stroke="{FLAG}" stroke-width="1.4"/>'
        f'<circle cx="{cx}" cy="{cy}" r="2" fill="{FLAG}"/>'
    )
    return "\n".join(parts)


def punch_holes(data: StudioData, cx: float, cy: float, r_max: float) -> str:
    rng = random.Random(int(data.seed, 16))
    parts: list[str] = []
    for ev in data.events:
        for k in range(ev.weight):
            r = 42 + (ev.dow + 0.5) * (r_max - 48) / 7 + rng.uniform(-5, 5)
            th = hour_theta(ev.hour + rng.uniform(-0.12, 0.12) + k * 0.04)
            x, y = polar(cx, cy, r, th)
            rad = 2.2 + (0.9 if ev.hour >= 21 or ev.hour <= 5 else 0)
            color = pigment_for(ev.repo)
            parts.append(
                f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{rad:.1f}" fill="{color}" opacity="0.92"/>'
            )
            if ev.hour >= 21 and rng.random() < 0.4:
                x2, y2 = polar(cx, cy, r + rng.uniform(6, 14), th + rng.uniform(-0.08, 0.08))
                parts.append(
                    f'<circle cx="{x2:.1f}" cy="{y2:.1f}" r="1.1" fill="{FLAG}" opacity="0.7"/>'
                )
    return "\n".join(parts)


def needle(data: StudioData, cx: float, cy: float, r_max: float) -> str:
    hour = data.generated.hour + data.generated.minute / 60
    th = hour_theta(hour)
    x, y = polar(cx, cy, r_max - 8, th)
    xb, yb = polar(cx, cy, 10, th + math.pi)
    return (
        f'<line x1="{xb:.1f}" y1="{yb:.1f}" x2="{x:.1f}" y2="{y:.1f}" '
        f'stroke="{FLAG}" stroke-width="1.6" stroke-linecap="round" opacity="0.85"/>'
        f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3.2" fill="{VOID}" stroke="{FLAG}" stroke-width="1.3"/>'
    )


def glyph_agro(cx: float, cy: float, r: float) -> str:
    bands = []
    for i in range(5):
        yy = cy - r * 0.15 + i * r * 0.18
        shade = BLEACH if i % 2 == 0 else BLEACH_DIM
        bands.append(
            f'<rect x="{cx - r * 0.62:.1f}" y="{yy:.1f}" width="{r * 1.24:.1f}" '
            f'height="{r * 0.14:.1f}" fill="{shade}" opacity="0.55"/>'
        )
    return (
        f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{INK}" stroke="{BLEACH}" stroke-width="1"/>'
        f'<path d="M {cx - r * 0.7:.1f},{cy - r * 0.15:.1f} Q {cx:.1f},{cy - r * 0.55:.1f} '
        f'{cx + r * 0.7:.1f},{cy - r * 0.15:.1f}" fill="none" stroke="{BLEACH_DIM}" '
        f'stroke-width="1.2" opacity="0.7"/>'
        + "".join(bands)
    )


def glyph_weather(cx: float, cy: float, r: float) -> str:
    arcs = []
    for i, rr in enumerate((r * 0.28, r * 0.48, r * 0.68)):
        arcs.append(
            f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{rr:.1f}" fill="none" stroke="{BLEACH}" '
            f'stroke-width="1" opacity="{0.25 + i * 0.18}" stroke-dasharray="2 4"/>'
        )
    return (
        f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{INK}" stroke="{BLEACH}" stroke-width="1"/>'
        + "".join(arcs)
        + f'<path d="M {cx - r * 0.55:.1f},{cy + r * 0.15:.1f} Q {cx:.1f},{cy - r * 0.2:.1f} '
        f'{cx + r * 0.55:.1f},{cy + r * 0.05:.1f}" fill="none" stroke="{FLAG}" '
        f'stroke-width="1.3" stroke-linecap="round"/>'
    )


def glyph_churn(cx: float, cy: float, r: float) -> str:
    rng = random.Random(17)
    dots = []
    for i in range(16):
        t = i / 15
        stay = 1 / (1 + math.exp((t - 0.55) * 8))
        px = cx - r * 0.55 + t * r * 1.1
        py = cy - r * 0.25 + (1 - stay) * r * 0.7 + rng.uniform(-3, 3)
        color = BLEACH if stay > 0.45 else FLAG
        dots.append(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="1.6" fill="{color}" opacity="0.85"/>')
    return (
        f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{INK}" stroke="{BLEACH}" stroke-width="1"/>'
        + "".join(dots)
    )


def plate_row() -> str:
    glyphs = (glyph_agro, glyph_weather, glyph_churn)
    parts: list[str] = []
    y, r = 628, 34
    x0 = 56
    for i, p in enumerate(PLATES):
        cx = x0 + i * 132 + r
        parts.append(glyphs[i](cx, y, r))
        parts.append(
            f'<text x="{cx + r + 10:.1f}" y="{y - 8:.1f}" font-family="{MONO}" font-size="9" '
            f'fill="{FLAG}" letter-spacing="0.14em">{p["n"]}</text>'
            f'<text x="{cx + r + 10:.1f}" y="{y + 8:.1f}" font-family="{SANS}" font-size="11" '
            f'fill="{BLEACH}">{esc(p["title"])}</text>'
            f'<text x="{cx + r + 10:.1f}" y="{y + 22:.1f}" font-family="{MONO}" font-size="8" '
            f'fill="{CAPTION}">{esc(p["note"])}</text>'
        )
    return "\n".join(parts)


def blotches(seed: str) -> str:
    rng = random.Random(int(seed, 16))
    parts: list[str] = []
    for _ in range(7):
        x = rng.uniform(40, 1100)
        y = rng.uniform(40, 680)
        rx, ry = rng.uniform(40, 160), rng.uniform(20, 90)
        rot = rng.uniform(-25, 25)
        parts.append(
            f'<ellipse cx="{x:.1f}" cy="{y:.1f}" rx="{rx:.1f}" ry="{ry:.1f}" '
            f'fill="{BLEACH}" opacity="{rng.uniform(0.03, 0.07)}" '
            f'transform="rotate({rot:.1f} {x:.1f} {y:.1f})"/>'
        )
    return "\n".join(parts)


def studio_svg(data: StudioData) -> str:
    iso = data.generated.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    source = "github" if data.from_api else "seeded"
    cx, cy, r_max = 818, 332, 248
    blot_seed = int(data.seed[:4], 16) % 97
    caption = (
        f"PLATE  ·  {iso}  ·  SEED {data.seed}  ·  "
        f"{data.commits_week} PUNCHES THIS WEEK  ·  NOW {data.currently.upper()}"
    )
    desc = (
        "Cyanotype meridian for Harish M: designer and data science student. "
        f"Punch holes from {data.commits_week} public commits this week. "
        f"Plates: Agro-Genix, weather, churn. Source {source}."
    )
    quiet = data.commits_week == 0
    quiet_note = (
        f'<text x="{cx}" y="{cy + 18}" text-anchor="middle" font-family="{MONO}" '
        f'font-size="10" fill="{CAPTION}" opacity="0.8">QUIET WEEK — NO PUNCHES</text>'
        if quiet
        else ""
    )
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="1200" height="720" role="img">
  <title>Harish M — cyanotype meridian</title>
  <desc>{esc(desc)}</desc>
  <defs>
    <linearGradient id="bath" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="{FIELD_LIFT}"/>
      <stop offset="55%" stop-color="{FIELD}"/>
      <stop offset="100%" stop-color="{VOID}"/>
    </linearGradient>
    <filter id="chem" x="-10%" y="-10%" width="120%" height="120%">
      <feTurbulence type="fractalNoise" baseFrequency="0.018" numOctaves="3" seed="{blot_seed}" result="n"/>
      <feColorMatrix type="matrix" values="0 0 0 0 0.08  0 0 0 0 0.28  0 0 0 0 0.42  0 0 0 0.22 0" result="tint"/>
      <feBlend in="SourceGraphic" in2="tint" mode="multiply"/>
    </filter>
    <clipPath id="typecol">
      <rect x="28" y="118" width="470" height="430"/>
    </clipPath>
  </defs>
  <rect width="{W}" height="{H}" fill="url(#bath)"/>
  <rect width="{W}" height="{H}" fill="{FIELD}" filter="url(#chem)" opacity="0.55"/>
  {blotches(data.seed)}
  {crop_marks()}
  <rect x="28" y="28" width="{W - 56}" height="{H - 56}" fill="none" stroke="{BLEACH}" stroke-width="0.6" opacity="0.25"/>
  <line x1="508" y1="48" x2="508" y2="560" stroke="{BLEACH}" stroke-width="0.6" opacity="0.22"/>

  <g clip-path="url(#typecol)" opacity="0.94">
    {wordmark_stack(44, 122, 196)}
  </g>

  <text transform="rotate(-90 22 360)" x="22" y="360" font-family="{MONO}" font-size="9"
        fill="{BLEACH_DIM}" letter-spacing="0.42em">HARISH M  ·  DESIGNER  ·  DATA</text>

  <text x="48" y="92" font-family="{MONO}" font-size="10" fill="{FLAG}" letter-spacing="0.28em">MERIDIAN</text>
  <text x="48" y="112" font-family="{SANS}" font-size="13" fill="{BLEACH_DIM}">A week, punched. Not a wall.</text>

  <g id="instrument" aria-hidden="true">
    {meridian_grid(cx, cy, r_max)}
    {punch_holes(data, cx, cy, r_max)}
    {needle(data, cx, cy, r_max)}
    {quiet_note}
  </g>

  {plate_row()}

  <text x="48" y="{H - 36}" font-family="{MONO}" font-size="9" fill="{CAPTION}">{esc(caption)}</text>
</svg>
"""


def wrap_text(body: str, width: int = 88) -> list[str]:
    words = body.split()
    lines: list[str] = []
    line = ""
    for word in words:
        trial = (line + " " + word).strip()
        if len(trial) > width:
            lines.append(line)
            line = word
        else:
            line = trial
    if line:
        lines.append(line)
    return lines


def inspect_svg(data: StudioData) -> str:
    iso = data.generated.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    IW, IH = 1200, 1080
    tokens = [
        ("Figma", "structure, type, frames"),
        ("Python", "runtime"),
        ("pandas", "tables"),
        ("scikit-learn", "estimators"),
        ("OpenCV / OCR", "unpinned print"),
    ]
    sections = [
        (
            "Intended use",
            "Interface and model work in the same week. Farmer-facing product, forecasting from tables, "
            "retention models. Seeking a data science or ML internship. Not a production ML engineer of record.",
        ),
        (
            "Training data",
            "Coursework in AI and data science. Project hours, not a private corpus: Agro-Genix (crop prices, "
            "storage booking), weather from historical records, telecom churn with class imbalance, CV and OCR "
            "for shelf prices. Public commits only.",
        ),
        (
            "Architecture",
            "Two stacks on one meridian. Figma for structure and type. Python, pandas, scikit-learn for the rest. "
            "Design decides what to measure. Models decide what the numbers allow.",
        ),
        (
            "Limitations",
            "Student work. Churn and weather are classical ML. Agro-Genix is product-shaped HTML, not a paper. "
            "No claim of production scale. Quiet weeks on this plate are empty on purpose.",
        ),
        (
            "Evaluation",
            "Good means a farmer can book storage without a tutorial; a forecast is honest about error; "
            "a churn model names the features that actually move. The plate should read as work, not a dashboard.",
        ),
    ]
    blocks: list[str] = []
    y = 196
    fig = 1
    for title, body in sections:
        blocks.append(
            f'<text x="72" y="{y}" font-family="{MONO}" font-size="11" fill="{FLAG}" '
            f'letter-spacing="0.16em">FIG.{fig:02d}  ·  {esc(title.upper())}</text>'
        )
        ly = y + 22
        for line in wrap_text(body):
            blocks.append(
                f'<text x="72" y="{ly}" font-family="{SANS}" font-size="16" fill="{BLEACH}" '
                f'opacity="0.9">{esc(line)}</text>'
            )
            ly += 24
        y = ly + 32
        fig += 1

    y += 8
    blocks.append(
        f'<text x="72" y="{y}" font-family="{MONO}" font-size="11" fill="{FLAG}" '
        f'letter-spacing="0.16em">FIG.{fig:02d}  ·  COMPONENTS</text>'
    )
    ty = y + 18
    tx = 72
    for name, role in tokens:
        holes = "".join(
            f'<circle cx="{tx + 16 + i * 10}" cy="{ty + 10}" r="2.1" fill="{VOID}" '
            f'stroke="{BLEACH}" stroke-width="0.6" opacity="0.7"/>'
            for i in range(5)
        )
        blocks.append(
            f'<rect x="{tx}" y="{ty}" width="196" height="56" fill="{INK}" stroke="{BLEACH}" '
            f'stroke-width="0.8" opacity="0.95"/>'
            f"{holes}"
            f'<text x="{tx + 12}" y="{ty + 32}" font-family="{SANS}" font-size="14" fill="{BLEACH}">{esc(name)}</text>'
            f'<text x="{tx + 12}" y="{ty + 46}" font-family="{MONO}" font-size="10" fill="{CAPTION}">{esc(role)}</text>'
        )
        tx += 208

    blot_seed = int(data.seed[:4], 16) % 97
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {IW} {IH}" width="1200" height="1080" role="img">
  <title>Harish M — inspect / filing plate</title>
  <desc>Product spec for Harish M as a system: intended use, training data, architecture, limitations, evaluation.</desc>
  <defs>
    <linearGradient id="bath2" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="{FIELD}"/>
      <stop offset="100%" stop-color="{VOID}"/>
    </linearGradient>
    <filter id="chem2">
      <feTurbulence type="fractalNoise" baseFrequency="0.02" numOctaves="3" seed="{blot_seed}"/>
      <feColorMatrix type="matrix" values="0 0 0 0 0.08  0 0 0 0 0.28  0 0 0 0 0.42  0 0 0 0.18 0"/>
      <feBlend in="SourceGraphic" mode="multiply"/>
    </filter>
  </defs>
  <rect width="{IW}" height="{IH}" fill="url(#bath2)"/>
  <rect width="{IW}" height="{IH}" fill="{FIELD}" filter="url(#chem2)" opacity="0.4"/>
  <rect x="28" y="28" width="{IW - 56}" height="{IH - 56}" fill="none" stroke="{BLEACH}" stroke-width="0.6" opacity="0.25"/>
  <text x="72" y="64" font-family="{MONO}" font-size="11" fill="{FLAG}" letter-spacing="0.32em">FILING COPY</text>
  <text x="72" y="108" font-family="{SANS}" font-size="42" fill="{BLEACH}" font-weight="700" letter-spacing="-0.04em">Harish M</text>
  <text x="72" y="136" font-family="{MONO}" font-size="11" fill="{CAPTION}">inspect  ·  {esc(iso)}  ·  seed {data.seed}</text>
  {''.join(blocks)}
  <text x="72" y="{IH - 36}" font-family="{MONO}" font-size="10" fill="{CAPTION}">now: {esc(data.currently)}  ·  {data.commits_week} punches this week</text>
</svg>
"""


def write(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def main() -> None:
    now = datetime.now(timezone.utc)
    data = fetch_activity(now)
    write(ROOT / "studio.svg", studio_svg(data))
    write(ROOT / "inspect.svg", inspect_svg(data))
    src = "API" if data.from_api else "fallback"
    print(f"studio.svg + inspect.svg  ({src}, seed={data.seed}, commits={data.commits_week})")


if __name__ == "__main__":
    main()
