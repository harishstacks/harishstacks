#!/usr/bin/env python3
"""
Nightly studio wall.

Fetches public GitHub activity for harishstacks and draws studio.svg.
inspect.svg is the quiet spec sheet. Same date + stats → same mural.
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
INK = "#1c1712"
OCHRE = "#c4a06a"
BLUE = "#6d7e8c"
PAPER = "#e6ddd0"
WALL = "#1f1b16"
WALL_LIFT = "#2a241c"
CAPTION = "#8a7f70"
CREAM = "#f3ece1"
PIGMENTS = (INK, OCHRE, BLUE)

PRINTS = [
    {
        "id": "agro",
        "title": "Agro-Genix",
        "note": "crop rates / storage — farmers first",
        "note_x": 76,
        "note_y": 560,
        "note_rot": -6,
        "x": 548,
        "y": 268,
        "rot": -3.4,
        "w": 196,
        "h": 248,
    },
    {
        "id": "weather",
        "title": "Weather",
        "note": "history → forecast",
        "note_x": 928,
        "note_y": 188,
        "note_rot": 8,
        "x": 742,
        "y": 198,
        "rot": 6.2,
        "w": 176,
        "h": 228,
    },
    {
        "id": "churn",
        "title": "Churn",
        "note": "who leaves, and why",
        "note_x": 760,
        "note_y": 658,
        "note_rot": -4,
        "x": 788,
        "y": 392,
        "rot": -5.1,
        "w": 188,
        "h": 236,
    },
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
    return PIGMENTS[h % 3]


def ink_paths(data: StudioData) -> str:
    rng = random.Random(int(data.seed, 16))
    parts: list[str] = []
    density = 0.35 + min(data.commits_week, 40) / 40 * 0.85
    # Quiet week: leave the wall. Busy week: more pressure.
    base_washes = 2 + int(density * 4)
    for i in range(base_washes):
        x0 = 48 + rng.uniform(0, 380)
        y0 = 168 + rng.uniform(0, 380)
        length = 90 + rng.uniform(40, 220) * density
        ang = rng.uniform(-0.9, 1.15)
        color = PIGMENTS[i % 3]
        op = 0.12 + density * 0.18
        parts.append(_stroke(x0, y0, length, ang, rng, color, op, 1.1 + density))

    for ev in data.events:
        for _ in range(ev.weight):
            x = 56 + ev.dow * 52 + ev.hour * 1.6 + rng.uniform(-14, 14)
            y = 190 + (ev.hour / 23) * 300 + rng.uniform(-22, 18)
            x = max(40, min(520, x))
            y = max(160, min(600, y))
            length = 28 + rng.uniform(12, 70) * (0.5 + density)
            ang = -0.4 + (ev.hour / 24) * 1.6 + rng.uniform(-0.35, 0.35)
            color = pigment_for(ev.repo)
            w = 0.7 + density * 1.4 + (1 if ev.hour >= 21 else 0)
            op = 0.22 + density * 0.28
            parts.append(_stroke(x, y, length, ang, rng, color, op, w))
            if ev.hour >= 21 and rng.random() < 0.45:
                parts.append(
                    f'<circle cx="{x + rng.uniform(-8, 8):.1f}" cy="{y + rng.uniform(-6, 8):.1f}" '
                    f'r="{rng.uniform(1.2, 3.4):.1f}" fill="{color}" opacity="{op * 0.7:.2f}"/>'
                )
    return "\n".join(parts)


def _stroke(
    x: float,
    y: float,
    length: float,
    ang: float,
    rng: random.Random,
    color: str,
    op: float,
    width: float,
) -> str:
    dx = math.cos(ang) * length
    dy = math.sin(ang) * length
    c1x = x + dx * 0.28 + rng.uniform(-22, 22)
    c1y = y + dy * 0.22 + rng.uniform(-18, 18)
    c2x = x + dx * 0.72 + rng.uniform(-16, 22)
    c2y = y + dy * 0.78 + rng.uniform(-16, 16)
    d = (
        f"M {x:.1f},{y:.1f} C {c1x:.1f},{c1y:.1f} "
        f"{c2x:.1f},{c2y:.1f} {x + dx:.1f},{y + dy:.1f}"
    )
    return (
        f'<path d="{d}" fill="none" stroke="{color}" '
        f'stroke-width="{width:.2f}" stroke-linecap="round" '
        f'stroke-linejoin="round" opacity="{op:.2f}"/>'
    )


def print_agro(x: float, y: float, w: float, h: float) -> str:
    inner = 14
    ix, iy = x + inner, y + inner
    iw, ih = w - inner * 2, h - inner * 2 - 36
    sky_h = ih * 0.38
    rows = []
    for i in range(6):
        yy = iy + sky_h + i * (ih - sky_h) / 6
        shade = OCHRE if i % 2 == 0 else "#9a7a48"
        rows.append(
            f'<rect x="{ix}" y="{yy:.1f}" width="{iw}" height="{(ih - sky_h) / 6 + 0.5:.1f}" fill="{shade}" opacity="0.9"/>'
        )
    return f"""
    <rect x="{ix}" y="{iy}" width="{iw}" height="{sky_h}" fill="{BLUE}" opacity="0.55"/>
    <rect x="{ix}" y="{iy + sky_h - 8}" width="{iw}" height="10" fill="#c9b089" opacity="0.5"/>
    {''.join(rows)}
    <rect x="{ix + iw * 0.72}" y="{iy + sky_h - 22}" width="18" height="22" fill="{INK}" opacity="0.35"/>
    """


def print_weather(x: float, y: float, w: float, h: float) -> str:
    inner = 14
    ix, iy = x + inner, y + inner
    iw, ih = w - inner * 2, h - inner * 2 - 36
    cx, cy = ix + iw * 0.5, iy + ih * 0.42
    arcs = []
    for i, r in enumerate((28, 46, 64)):
        arcs.append(
            f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r}" fill="none" stroke="{BLUE}" '
            f'stroke-width="1.1" opacity="{0.25 + i * 0.12}" '
            f'stroke-dasharray="3 5"/>'
        )
    return f"""
    <rect x="{ix}" y="{iy}" width="{iw}" height="{ih}" fill="#d9d2c6"/>
    {''.join(arcs)}
    <path d="M {ix + 18:.1f},{iy + ih * 0.62:.1f} C {ix + iw * 0.3:.1f},{iy + ih * 0.45:.1f} {ix + iw * 0.55:.1f},{iy + ih * 0.78:.1f} {ix + iw - 16:.1f},{iy + ih * 0.58:.1f}"
          fill="none" stroke="{INK}" stroke-width="1.4" opacity="0.45" stroke-linecap="round"/>
    <ellipse cx="{cx - 18:.1f}" cy="{cy - 8:.1f}" rx="22" ry="10" fill="{PAPER}" opacity="0.7"/>
    <ellipse cx="{cx + 6:.1f}" cy="{cy - 12:.1f}" rx="16" ry="8" fill="{PAPER}" opacity="0.55"/>
    """


def print_churn(x: float, y: float, w: float, h: float) -> str:
    inner = 14
    ix, iy = x + inner, y + inner
    iw, ih = w - inner * 2, h - inner * 2 - 36
    rng = random.Random(17)
    dots = []
    for i in range(28):
        px = ix + 10 + (i / 27) * (iw - 20)
        stay = 1 / (1 + math.exp((i - 16) / 3.2))
        py = iy + ih * 0.22 + (1 - stay) * ih * 0.55 + rng.uniform(-6, 6)
        color = BLUE if stay > 0.45 else OCHRE
        dots.append(
            f'<circle cx="{px:.1f}" cy="{py:.1f}" r="{1.4 + rng.random()}" fill="{color}" opacity="0.7"/>'
        )
    return f"""
    <rect x="{ix}" y="{iy}" width="{iw}" height="{ih}" fill="#ddd6cb"/>
    <path d="M {ix + 8:.1f},{iy + ih * 0.28:.1f} C {ix + iw * 0.42:.1f},{iy + ih * 0.22:.1f} {ix + iw * 0.58:.1f},{iy + ih * 0.78:.1f} {ix + iw - 10:.1f},{iy + ih * 0.72:.1f}"
          fill="none" stroke="{INK}" stroke-width="1.3" opacity="0.55"/>
    {''.join(dots)}
    """


def print_price_thumb() -> str:
    x, y, w, h, rot = 992, 498, 72, 88, 11.5
    tags = []
    for i in range(4):
        tx = x + 12 + (i % 2) * 22
        ty = y + 14 + (i // 2) * 24
        tags.append(
            f'<rect x="{tx}" y="{ty}" width="18" height="12" rx="1" fill="none" stroke="{INK}" '
            f'stroke-width="0.7" opacity="0.35"/>'
        )
    return f"""
    <g transform="rotate({rot} {x + w/2} {y + h/2})" opacity="0.5">
      <rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{CREAM}" stroke="{INK}" stroke-width="0.6" opacity="0.85"/>
      {''.join(tags)}
    </g>
    """


def polaroid(p: dict, inner: str) -> str:
    x, y, w, h, rot = p["x"], p["y"], p["w"], p["h"], p["rot"]
    cx, cy = x + w / 2, y + h / 2
    tape_w, tape_h = 36, 10
    nx, ny, nr = p["note_x"], p["note_y"], p["note_rot"]
    return f"""
    <g transform="rotate({rot} {cx:.1f} {cy:.1f})">
      <rect x="{x + 4}" y="{y + 6}" width="{w}" height="{h}" fill="#0d0b09" opacity="0.35"/>
      <rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{CREAM}"/>
      {inner}
      <text x="{x + 14}" y="{y + h - 14}" font-family="Georgia, 'Times New Roman', serif"
            font-size="11" fill="{INK}" opacity="0.8">{esc(p["title"])}</text>
      <rect x="{x + w * 0.5 - tape_w / 2}" y="{y - 5}" width="{tape_w}" height="{tape_h}"
            fill="{OCHRE}" opacity="0.45" transform="rotate(-8 {x + w * 0.5} {y})"/>
    </g>
    <text x="{nx}" y="{ny}" font-family="Georgia, 'Times New Roman', serif" font-style="italic"
          font-size="13" fill="{OCHRE}" opacity="0.8"
          transform="rotate({nr} {nx} {ny})">{esc(p["note"])}</text>
    """


def studio_svg(data: StudioData) -> str:
    iso = data.generated.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    caption = (
        f"generated {iso}  ·  seed {data.seed}  ·  "
        f"{data.commits_week} commits this week  ·  currently: {data.currently}"
    )
    source = "github" if data.from_api else "seeded"
    agro = PRINTS[0]
    weather = PRINTS[1]
    churn = PRINTS[2]
    desc = (
        "Studio wall for Harish M: designer and data science student. "
        f"Ink density from {data.commits_week} public commits this week. "
        f"Prints: Agro-Genix, weather forecasting, customer churn. Source {source}."
    )
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="1200" height="720" role="img">
  <title>Harish M — nightly studio wall</title>
  <desc>{esc(desc)}</desc>
  <defs>
    <filter id="grain" x="0" y="0" width="100%" height="100%">
      <feTurbulence type="fractalNoise" baseFrequency="0.85" numOctaves="4" seed="2" result="n"/>
      <feColorMatrix type="saturate" values="0"/>
      <feComponentTransfer>
        <feFuncA type="table" tableValues="0 0.14"/>
      </feComponentTransfer>
      <feBlend in="SourceGraphic" mode="multiply"/>
    </filter>
    <linearGradient id="wall" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="{WALL_LIFT}"/>
      <stop offset="100%" stop-color="{WALL}"/>
    </linearGradient>
  </defs>
  <rect width="{W}" height="{H}" fill="url(#wall)"/>
  <rect width="{W}" height="{H}" fill="{WALL}" filter="url(#grain)" opacity="0.55"/>
  <line x1="72" y1="96" x2="72" y2="128" stroke="{OCHRE}" stroke-width="1.2" opacity="0.35"/>
  <circle cx="72" cy="92" r="3.2" fill="none" stroke="{OCHRE}" stroke-width="1" opacity="0.5"/>
  <line x1="72" y1="640" x2="430" y2="640" stroke="{INK}" stroke-width="0.6" opacity="0.18"/>

  <text x="72" y="188" font-family="Georgia, 'Times New Roman', Palatino, serif"
        font-size="72" fill="{PAPER}">{esc("Harish M")}</text>
  <text x="76" y="224" font-family="Georgia, 'Times New Roman', serif" font-style="italic"
        font-size="18" fill="{OCHRE}" opacity="0.85">Designer. Data, on the wall.</text>

  <g id="ink" aria-hidden="true">
    {ink_paths(data)}
  </g>

  {polaroid(agro, print_agro(agro["x"], agro["y"], agro["w"], agro["h"]))}
  {polaroid(weather, print_weather(weather["x"], weather["y"], weather["w"], weather["h"]))}
  {polaroid(churn, print_churn(churn["x"], churn["y"], churn["w"], churn["h"]))}
  {print_price_thumb()}

  <text x="72" y="{H - 28}" font-family="ui-monospace, SFMono-Regular, Menlo, Consolas, monospace"
        font-size="10" fill="{CAPTION}">{esc(caption)}</text>
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
            "Two stacks that share a wall. Figma for structure and type. Python, pandas, scikit-learn for the rest. "
            "Design decides what to measure. Models decide what the numbers allow.",
        ),
        (
            "Limitations",
            "Student work. Churn and weather are classical ML. Agro-Genix is product-shaped HTML, not a paper. "
            "No claim of production scale. Quiet weeks on this wall are empty on purpose.",
        ),
        (
            "Evaluation",
            "Good means a farmer can book storage without a tutorial; a forecast is honest about error; "
            "a churn model names the features that actually move. The wall should read as work, not a dashboard.",
        ),
    ]
    blocks: list[str] = []
    y = 168
    for title, body in sections:
        blocks.append(
            f'<text x="72" y="{y}" font-family="ui-monospace, SFMono-Regular, Menlo, Consolas, monospace" '
            f'font-size="11" fill="{OCHRE}" letter-spacing="0.12em">{esc(title.upper())}</text>'
        )
        ly = y + 22
        for line in wrap_text(body):
            blocks.append(
                f'<text x="72" y="{ly}" font-family="Georgia, \'Times New Roman\', serif" '
                f'font-size="16" fill="{PAPER}" opacity="0.88">{esc(line)}</text>'
            )
            ly += 24
        y = ly + 32

    y += 8
    blocks.append(
        f'<text x="72" y="{y}" font-family="ui-monospace, SFMono-Regular, Menlo, Consolas, monospace" '
        f'font-size="11" fill="{OCHRE}" letter-spacing="0.12em">COMPONENTS</text>'
    )
    ty = y + 18
    tx = 72
    for name, role in tokens:
        blocks.append(
            f'<rect x="{tx}" y="{ty}" width="196" height="52" fill="none" stroke="{OCHRE}" '
            f'stroke-width="0.8" opacity="0.45"/>'
            f'<text x="{tx + 12}" y="{ty + 22}" font-family="Georgia, \'Times New Roman\', serif" '
            f'font-size="14" fill="{PAPER}">{esc(name)}</text>'
            f'<text x="{tx + 12}" y="{ty + 40}" font-family="ui-monospace, SFMono-Regular, Menlo, Consolas, monospace" '
            f'font-size="10" fill="{CAPTION}">{esc(role)}</text>'
        )
        tx += 208

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {IW} {IH}" width="1200" height="1080" role="img">
  <title>Harish M — inspect / model card</title>
  <desc>Product spec for Harish M as a system: intended use, training data, architecture, limitations, evaluation.</desc>
  <defs>
    <linearGradient id="wall2" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="{WALL_LIFT}"/>
      <stop offset="100%" stop-color="{WALL}"/>
    </linearGradient>
  </defs>
  <rect width="{IW}" height="{IH}" fill="url(#wall2)"/>
  <text x="72" y="88" font-family="Georgia, 'Times New Roman', Palatino, serif"
        font-size="36" fill="{PAPER}">Harish M</text>
  <text x="72" y="118" font-family="ui-monospace, SFMono-Regular, Menlo, Consolas, monospace"
        font-size="11" fill="{CAPTION}">model card  ·  {esc(iso)}  ·  seed {data.seed}</text>
  {''.join(blocks)}
  <text x="72" y="{IH - 36}" font-family="ui-monospace, SFMono-Regular, Menlo, Consolas, monospace"
        font-size="10" fill="{CAPTION}">currently: {esc(data.currently)}  ·  {data.commits_week} commits this week</text>
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
