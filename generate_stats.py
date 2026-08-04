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

# Theme palette (matches existing README dark theme)
BG = "#0D1117"
TITLE = "#22D3EE"
TEXT = "#F0F6FC"
SUBTEXT = "#8B949E"
ACCENT = "#22D3EE"
ICON = "#22D3EE"
BORDER = "#30363D"
CARD_W = 460
CARD_H = 195


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
            f'  <text x="{icon_x}" y="{y}" font-size="16" fill="{ICON}" font-family="Segoe UI Emoji, Apple Color Emoji, sans-serif">{esc(icon)}</text>\n'
            f'  <text x="{label_x}" y="{y}" font-size="14" fill="{TEXT}" font-family="Segoe UI, Helvetica, Arial, sans-serif">{esc(label)}</text>\n'
            f'  <text x="{value_x}" y="{y}" font-size="14" font-weight="bold" fill="{TEXT}" text-anchor="end" font-family="Segoe UI, Helvetica, Arial, sans-serif">{esc(value)}</text>'
        )

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{CARD_W}" height="{CARD_H}" viewBox="0 0 {CARD_W} {CARD_H}">
  <rect width="{CARD_W}" height="{CARD_H}" rx="11" fill="{BG}" stroke="{BORDER}" stroke-width="1"/>
  <text x="25" y="38" font-size="18" font-weight="bold" fill="{TITLE}" font-family="Segoe UI, Helvetica, Arial, sans-serif">📊 GitHub Stats</text>
  <line x1="25" y1="50" x2="{CARD_W-25}" y2="50" stroke="{BORDER}" stroke-width="1"/>
{chr(10).join(rows_svg)}
  <text x="{CARD_W-25}" y="{CARD_H-12}" font-size="9" fill="{SUBTEXT}" text-anchor="end" font-family="Segoe UI, Helvetica, Arial, sans-serif">Updated {datetime.now(timezone.utc).strftime("%b %Y")}</text>
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
    palette = ["#3776AB", "#F7DF1E", "#3178C6", "#E34F26", "#563D7C", "#A855F7", "#F7931E", "#DC382D"]

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
            f'  <text x="{label_x}" y="{y}" font-size="13" fill="{TEXT}" font-family="Segoe UI, Helvetica, Arial, sans-serif">{esc(lang)}</text>\n'
            f'  <rect x="{bar_x}" y="{y-11}" width="{bar_w}" height="11" rx="3" fill="{BORDER}"/>\n'
            f'  <rect x="{bar_x}" y="{y-11}" width="{w}" height="11" rx="3" fill="{color}"/>\n'
            f'  <text x="{CARD_W-30}" y="{y}" font-size="11" fill="{SUBTEXT}" text-anchor="end" font-family="Segoe UI, Helvetica, Arial, sans-serif">{pct:.1f}%</text>'
        )

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{CARD_W}" height="{CARD_H}" viewBox="0 0 {CARD_W} {CARD_H}">
  <rect width="{CARD_W}" height="{CARD_H}" rx="11" fill="{BG}" stroke="{BORDER}" stroke-width="1"/>
  <text x="25" y="38" font-size="18" font-weight="bold" fill="{TITLE}" font-family="Segoe UI, Helvetica, Arial, sans-serif">💻 Top Languages</text>
  <line x1="25" y1="50" x2="{CARD_W-25}" y2="50" stroke="{BORDER}" stroke-width="1"/>
{chr(10).join(rows_svg)}
  <text x="{CARD_W-25}" y="{CARD_H-12}" font-size="9" fill="{SUBTEXT}" text-anchor="end" font-family="Segoe UI, Helvetica, Arial, sans-serif">Updated {datetime.now(timezone.utc).strftime("%b %Y")}</text>
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