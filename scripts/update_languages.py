"""Build bilingual profile charts from public, non-fork repository language bytes."""
import json
import os
import re
from collections import Counter
from datetime import timezone, datetime
from html import escape
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
COLORS = {"JavaScript": "#f1e05a", "TypeScript": "#3178c6", "Python": "#f0a44b", "HTML": "#e34c26", "CSS": "#563d7c", "Shell": "#89e051", "Java": "#b07219", "C++": "#f34b7d", "SCSS": "#c6538c", "Jupyter Notebook": "#da5b0b"}


def get_json(path):
    headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2026-03-10", "User-Agent": "profile-language-chart"}
    token = os.environ.get("GH_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    with urlopen(Request(f"https://api.github.com{path}", headers=headers), timeout=30) as response:
        return json.load(response)


def collect(owner, fetch=get_json):
    totals = Counter()
    count = 0
    page = 1
    while True:
        repos = fetch(f"/users/{quote(owner)}/repos?type=owner&per_page=100&page={page}")
        if not isinstance(repos, list):
            raise ValueError("Invalid repository list")
        for repo in repos:
            if not isinstance(repo, dict) or not isinstance(repo.get("name"), str):
                raise ValueError("Invalid repository metadata")
            # The profile is presentation material, not a software project.
            if repo.get("fork") or repo.get("private") or repo["name"].lower() == owner.lower():
                continue
            languages = fetch(f"/repos/{quote(owner)}/{quote(repo['name'], safe='')}/languages")
            if not isinstance(languages, dict) or any(not isinstance(name, str) or type(size) is not int or size < 0 for name, size in languages.items()):
                raise ValueError("Invalid language response")
            if sum(languages.values()):
                count += 1
                totals.update(languages)
        if len(repos) < 100:
            break
        page += 1
    if not sum(totals.values()):
        raise ValueError("No language data available; keeping the previous charts")
    return totals, count


def shares(totals):
    # Largest remainder rounding keeps the displayed percentages at exactly 100.0%.
    items = sorted(((name, size) for name, size in totals.items() if size > 0), key=lambda item: (-item[1], item[0]))
    total = sum(size for _, size in items)
    units = [size * 1000 // total for _, size in items]
    order = sorted(range(len(items)), key=lambda i: -(items[i][1] * 1000 % total))
    for index in order[:1000 - sum(units)]:
        units[index] += 1
    return [(name, size, value / 10) for (name, size), value in zip(items, units)]


def chart(totals, count, day, language):
    rows = shares(totals)
    de = language == "de"
    title = "Meine Sprachen im Code" if de else "My languages in code"
    subtitle = f"{count} öffentliche Original-Repositories · Codegröße in Bytes" if de else f"{count} public original repositories · code size in bytes"
    updated = ("Aktualisiert" if de else "Updated") + f": {day.isoformat()} · UTC"
    height = 174 + 34 * len(rows)
    content = [f'<svg xmlns="http://www.w3.org/2000/svg" width="760" height="{height}" viewBox="0 0 760 {height}" role="img" aria-labelledby="title desc">',
               f'<title id="title">{title}</title>',
               f'<desc id="desc">{escape(subtitle)}. ' + escape(', '.join(f'{name}: {percent:.1f}%' for name, _, percent in rows)) + '</desc>',
               f'<rect x="1" y="1" width="758" height="{height - 2}" rx="18" fill="#0d1117" stroke="#30363d"/>',
               '<g font-family="Arial, Helvetica, sans-serif">',
               f'<text x="28" y="40" fill="#f0f6fc" font-size="22" font-weight="700">{title}</text>',
               f'<text x="28" y="65" fill="#a5b1bf" font-size="13">{escape(subtitle)}</text>',
               '<defs><clipPath id="bar"><rect x="28" y="86" width="704" height="14" rx="7"/></clipPath></defs>',
               '<g clip-path="url(#bar)">']
    offset = 28.0
    total = sum(totals.values())
    for name, size, _ in rows:
        width = 704 * size / total
        content.append(f'<rect x="{offset:.3f}" y="86" width="{width:.3f}" height="14" fill="{COLORS.get(name, "#73bcae")}"/>')
        offset += width
    content.append('</g>')
    for index, (name, _, percent) in enumerate(rows):
        y = 135 + index * 34
        label = f"{percent:.1f}".replace('.', ',') if de else f"{percent:.1f}"
        content.extend([f'<circle cx="35" cy="{y - 5}" r="5" fill="{COLORS.get(name, "#73bcae")}"/>',
                        f'<text x="52" y="{y}" fill="#f0f6fc" font-size="15">{escape(name)}</text>',
                        f'<text x="732" y="{y}" fill="#c9d1d9" font-size="15" text-anchor="end">{label} %</text>'])
    content.append(f'<text x="28" y="{height - 23}" fill="#a5b1bf" font-size="12">{escape(updated)}</text></g></svg>\n')
    return '\n'.join(content)


def main():
    owner = os.environ.get("PROFILE_OWNER", "michkffm")
    if not re.fullmatch(r"[A-Za-z0-9-]{1,39}", owner):
        raise ValueError("Invalid profile owner")
    totals, count = collect(owner)
    today = datetime.now(timezone.utc).date()
    # Finish all API reads before writing, so incomplete results never replace the chart.
    for language in ("de", "en"):
        (ROOT / "assets" / f"languages-{language}.svg").write_text(chart(totals, count, today, language), encoding="utf-8")
    print(f"Updated language charts from {count} public original repositories.")


if __name__ == "__main__":
    main()
