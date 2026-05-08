#!/usr/bin/env python3
"""
Enhance starz category READMEs to add ⭐ stars and 🍴 forks columns.
Run: python3 enhance_readmes.py
"""

import json
import os
import re
import subprocess
import urllib.request
from pathlib import Path

REPO_DIR = Path(__file__).parent
CATS = {
    "ai-agents-llm": {"name": "🤖 AI AGENTS & LLM"},
    "rag-knowledge":  {"name": "🧠 RAG & KNOWLEDGE BASE"},
    "python-tools":   {"name": "🐍 PYTHON TOOLS & DATA"},
    "web-ui":         {"name": "🌐 WEB & UI"},
    "dev-infra":      {"name": "⚙️  DEV INFRA & TOOLING"},
    "rust-systems":   {"name": "🔧 RUST & SYSTEMS"},
    "data-analytics": {"name": "📊 DATA & ANALYTICS"},
    "cloud-deploy":   {"name": "☁️  CLOUD & DEPLOY"},
}

def get_token():
    token = os.environ.get('GH_TOKEN')
    if not token:
        try:
            token = subprocess.check_output(['gh', 'auth', 'token'], text=True).strip()
        except Exception:
            raise SystemExit("GH_TOKEN not set and `gh auth token` failed")
    return token

def fetch_repo_info(full_name, token):
    """Fetch stars/forks/description for a single repo via API."""
    url = f"https://api.github.com/repos/{full_name}"
    req = urllib.request.Request(url, headers={
        'Authorization': f'token {token}',
        'Accept': 'application/vnd.github+json',
        'X-GitHub-Api-Version': '2022-11-28',
        'User-Agent': 'starz-enhance/1.0'
    })
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
            return {
                'stars': data.get('stargazers_count', 0),
                'forks': data.get('forks_count', 0),
                'desc':  data.get('description') or '',
                'lang':  data.get('language') or '—',
                'lic':   (data.get('license') or {}).get('name', '—') if isinstance(data.get('license'), dict) else '—',
                'topics': data.get('topics') or [],
            }
    except Exception as e:
        print(f"   ⚠️  Failed to fetch {full_name}: {e}")
        return None

def build_enhanced_table(readme_path, cat_slug, token):
    """Parse existing table, fetch fresh stats, rebuild with stars/forks."""
    content = readme_path.read_text()

    # Extract rows from existing table
    old_header = "| # | Repository | Language | Description |"
    new_header = "| # | Repository | Language | ⭐ | 🍴 | Description |"

    # Also update the actual header text in content
    content = content.replace(old_header, new_header)

    if old_header not in content:
        print(f"   ⚠️  Unexpected table format in {readme_path.name}, skipping")
        return

    lines = content.splitlines()
    # Find the table lines (starting after header line ---)
    table_start = None
    for i, line in enumerate(lines):
        if re.match(r'\|\s*#\s*\|', line):
            table_start = i
            break

    if table_start is None:
        print(f"   ⚠️  Could not find table start in {readme_path.name}")
        return

    # Split into header, separator, and rows
    header_line = lines[table_start]
    sep_line    = lines[table_start + 1]
    data_lines  = []
    for line in lines[table_start + 2:]:
        if re.match(r'\|\s*\d+\s*\|', line):
            data_lines.append(line)
        else:
            break

    # Process each row
    updated_lines = []
    for line in data_lines:
        # Parse: | N | [owner/repo](url) | lang | description |
        parts = [p.strip() for p in line.split('|')]
        # parts: ['', 'N', 'owner/repo', 'lang', 'description', '']
        if len(parts) < 5:
            continue

        n   = parts[1]
        repo_md = parts[2]  # e.g. [666ghj/BettaFish](https://github.com/666ghj/BettaFish)
        lang = parts[3]
        desc = parts[4]

        # Extract owner/repo from markdown link
        match = re.search(r'\((https?://github\.com/([^)]+))\)', repo_md)
        if not match:
            updated_lines.append(line)
            continue

        full_name = match.group(2)  # e.g. "666ghj/BettaFish"

        # Fetch fresh data
        info = fetch_repo_info(full_name, token)
        if info is None:
            updated_lines.append(line)
            continue

        # Format stars/forks with emoji for very popular repos
        stars_str = f"{info['stars']:,}" if info['stars'] else "—"
        forks_str = f"{info['forks']:,}" if info['forks'] else "—"

        new_row = f"| {n} | [{full_name}](https://github.com/{full_name}) | {lang} | {stars_str} | {forks_str} | {desc} |"
        updated_lines.append(new_row)

    # Rebuild the section
    new_sep = sep_line.replace('|---|', '|---|---|---|').replace('|----------|', '|----:|')
    # Fix separator: original is |---|----------|-------------|
    # We need:     |---|---|---|---|-------------|
    # Count columns: #, Repository, Language, ⭐, 🍴, Description = 6 cols
    new_sep = "|---|---|---|---|---|---|"

    new_lines = lines[:table_start] + [header_line, new_sep] + updated_lines + lines[table_start + 2 + len(data_lines):]

    readme_path.write_text('\n'.join(new_lines) + '\n')
    print(f"   ✅ {readme_path.name}: enhanced {len(updated_lines)} rows")

def main():
    token = get_token()
    print(f"✅ Authenticated\n")

    for slug in CATS:
        readme_path = REPO_DIR / slug / 'README.md'
        if not readme_path.exists():
            print(f"⚠️  {slug}/README.md not found, skipping")
            continue

        print(f"🔄 Processing {CATS[slug]['name']}...")
        build_enhanced_table(readme_path, slug, token)

    print("\n✅ All category READMEs enhanced with ⭐ stars and 🍴 forks!")

if __name__ == '__main__':
    main()
