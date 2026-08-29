#!/usr/bin/env python3
"""
Generate custom GitHub Stats and Top Languages SVG cards.

Uses the authenticated GitHub API (GITHUB_TOKEN env var) to avoid the
rate-limited public github-readme-stats Vercel instances. The generated
SVGs are committed to dist/ and served from raw.githubusercontent.com,
guaranteeing zero broken images.

Usage:
    GITHUB_TOKEN=ghp_xxx python generate_stats.py

Outputs:
    dist/stats.svg
    dist/top-langs.svg
"""

import os
import sys
import json
import urllib.request
import urllib.error
from datetime import datetime, timezone

USER = os.environ.get("GITHUB_REPOSITORY_OWNER") or os.environ.get("STATS_USER") or "harishstacks"
TOKEN = os.environ.get("GITHUB_TOKEN", "")

# Theme palette (matches command-center README)
BG = "#060812"
PANEL = "#080c19"
TITLE = "#00d2ff"
TEXT = "#e2e8f0"
SUBTEXT = "#64748b"
ACCENT = "#00d2ff"
ICON = "#00d2ff"
BORDER = "#1a2740"
MUTED_BAR = "#12182b"
CARD_W = 460
CARD_H = 195
FONT = "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace"


def gh_get(url):
    headers = {
        "User-Agent": "harishstacks-stats-generator",
        "Accept": "application/vnd.github+json",
    }
    if TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())


def fetch_user():
    return gh_get(f"https://api.github.com/users/{USER}")


def fetch_repos():
    repos = []
    page = 1
    while True:
        batch = gh_get(f"https://api.github.com/users/{USER}/repos?per_page=100&page={page}&type=owner")
        if not batch:
            break
        repos.extend(batch)
        if len(batch) < 100:
            break
        page += 1
    return repos


def esc(text):
    # Use chr() to avoid editor auto-formatting unescaping HTML entities
    amp = chr(38)  # &
    lt = chr(60)   # <
    gt = chr(62)   # >
    return (text or "").replace(amp, amp + "amp;").replace(lt, amp + "lt;").replace(gt, amp + "gt;")


def fmt(n):
    if n >= 1000:
        return f"{n/1000:.1f}k"
    return str(n)


def stats_svg(user, repos):
    stars = sum(r.get("stargazers_count", 0) for r in repos)
    forks = sum(r.get("forks_count", 0) for r in repos)
    pub = user.get("public_repos", len(repos))
    followers = user.get("followers", 0)
    following = user.get("following", 0)

    rows = [
        ("★", "Total Stars", fmt(stars)),
        ("⑂", "Total Forks", fmt(forks)),
        ("📦", "Repositories", fmt(pub)),
        ("👥", "Followers", fmt(followers)),
        ("👁", "Following", fmt(following)),
    ]

    y0 = 70
    row_h = 24
    icon_x = 30
    label_x = 60
    value_x = CARD_W - 30

    rows_svg = []
    for i, (icon, label, value) in enumerate(rows):
        y = y0 + i * row_h
        rows_svg.append(
            f'  <text x="{icon_x}" y="{y}" font-size="13" fill="{ICON}" font-family="{FONT}">{esc(icon)}</text>\n'
            f'  <text x="{label_x}" y="{y}" font-size="13" fill="{TEXT}" font-family="{FONT}">{esc(label)}</text>\n'
            f'  <text x="{value_x}" y="{y}" font-size="13" font-weight="bold" fill="{TITLE}" text-anchor="end" font-family="{FONT}">{esc(value)}</text>'
        )

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{CARD_W}" height="{CARD_H}" viewBox="0 0 {CARD_W} {CARD_H}">
  <defs>
    <linearGradient id="sedge" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#00d2ff" stop-opacity="0.55"/>
      <stop offset="50%" stop-color="#7000ff" stop-opacity="0.28"/>
      <stop offset="100%" stop-color="#00d2ff" stop-opacity="0.12"/>
    </linearGradient>
    <linearGradient id="sline" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#00d2ff" stop-opacity="0.7"/>
      <stop offset="100%" stop-color="#7000ff" stop-opacity="0"/>
    </linearGradient>
  </defs>
  <rect width="{CARD_W}" height="{CARD_H}" rx="12" fill="{BG}"/>
  <rect x="0.6" y="0.6" width="{CARD_W-1.2}" height="{CARD_H-1.2}" rx="11.4" fill="{PANEL}" stroke="url(#sedge)" stroke-width="1.2"/>
  <circle cx="28" cy="28" r="3.2" fill="{TITLE}"/>
  <text x="40" y="33" font-size="13" font-weight="bold" fill="{TITLE}" font-family="{FONT}" letter-spacing="1.5">GITHUB STATS</text>
  <line x1="25" y1="46" x2="{CARD_W-25}" y2="46" stroke="url(#sline)" stroke-width="1"/>
{chr(10).join(rows_svg)}
  <text x="{CARD_W-25}" y="{CARD_H-12}" font-size="9" fill="{SUBTEXT}" text-anchor="end" font-family="{FONT}">Updated {datetime.now(timezone.utc).strftime("%b %Y")}</text>
</svg>'''


def top_langs_svg(repos):
    # Weight by number of repos using each language (repo size in KB is
    # dominated by dependencies/assets and misrepresents actual usage).
    # Forks are excluded so the card reflects the user's own work.
    langs = {}
    for r in repos:
        if r.get("fork"):
            continue
        lang = r.get("language")
        if not lang:
            continue
        langs[lang] = langs.get(lang, 0) + 1

    if not langs:
        langs = {"Python": 1}

    total = sum(langs.values())
    top = sorted(langs.items(), key=lambda x: -x[1])[:6]

    # Color palette for language bars
    palette = ["#00d2ff", "#7000ff", "#00f0ff", "#9d4edd", "#22d3ee", "#a855f7", "#67e8f9", "#c084fc"]

    y0 = 70
    row_h = 22
    bar_x = 150
    bar_w = CARD_W - bar_x - 30
    label_x = 30

    rows_svg = []
    for i, (lang, val) in enumerate(top):
        y = y0 + i * row_h
        pct = (val / total) * 100
        color = palette[i % len(palette)]
        w = max(int(bar_w * pct / 100), 2)
        rows_svg.append(
            f'  <text x="{label_x}" y="{y}" font-size="12" fill="{TEXT}" font-family="{FONT}">{esc(lang)}</text>\n'
            f'  <rect x="{bar_x}" y="{y-11}" width="{bar_w}" height="8" rx="4" fill="{MUTED_BAR}"/>\n'
            f'  <rect x="{bar_x}" y="{y-11}" width="{w}" height="8" rx="4" fill="{color}"/>\n'
            f'  <text x="{CARD_W-30}" y="{y}" font-size="11" fill="{SUBTEXT}" text-anchor="end" font-family="{FONT}">{pct:.1f}%</text>'
        )

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{CARD_W}" height="{CARD_H}" viewBox="0 0 {CARD_W} {CARD_H}">
  <defs>
    <linearGradient id="ledge" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#00d2ff" stop-opacity="0.55"/>
      <stop offset="50%" stop-color="#7000ff" stop-opacity="0.28"/>
      <stop offset="100%" stop-color="#00d2ff" stop-opacity="0.12"/>
    </linearGradient>
    <linearGradient id="lline" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#00d2ff" stop-opacity="0.7"/>
      <stop offset="100%" stop-color="#7000ff" stop-opacity="0"/>
    </linearGradient>
  </defs>
  <rect width="{CARD_W}" height="{CARD_H}" rx="12" fill="{BG}"/>
  <rect x="0.6" y="0.6" width="{CARD_W-1.2}" height="{CARD_H-1.2}" rx="11.4" fill="{PANEL}" stroke="url(#ledge)" stroke-width="1.2"/>
  <circle cx="28" cy="28" r="3.2" fill="{TITLE}"/>
  <text x="40" y="33" font-size="13" font-weight="bold" fill="{TITLE}" font-family="{FONT}" letter-spacing="1.5">TOP LANGUAGES</text>
  <line x1="25" y1="46" x2="{CARD_W-25}" y2="46" stroke="url(#lline)" stroke-width="1"/>
{chr(10).join(rows_svg)}
  <text x="{CARD_W-25}" y="{CARD_H-12}" font-size="9" fill="{SUBTEXT}" text-anchor="end" font-family="{FONT}">Updated {datetime.now(timezone.utc).strftime("%b %Y")}</text>
</svg>'''


def main():
    os.makedirs("dist", exist_ok=True)
    print(f"Fetching GitHub data for {USER}...")
    user = fetch_user()
    repos = fetch_repos()
    print(f"  user: repos={user.get('public_repos')} followers={user.get('followers')}")
    print(f"  fetched {len(repos)} repositories")

    stats = stats_svg(user, repos)
    with open("dist/stats.svg", "w", encoding="utf-8") as f:
        f.write(stats)
    print("✓ wrote dist/stats.svg")

    langs = top_langs_svg(repos)
    with open("dist/top-langs.svg", "w", encoding="utf-8") as f:
        f.write(langs)
    print("✓ wrote dist/top-langs.svg")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"✗ ERROR: {e}", file=sys.stderr)
        raise