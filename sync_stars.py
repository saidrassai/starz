#!/usr/bin/env python3
"""
starz sync script — fetches all starred repos and regenerates the folder structure.
Run: python3 sync_stars.py
"""

import json
import os
import subprocess
from pathlib import Path

REPO_DIR = Path(__file__).parent

# ── Categories ──────────────────────────────────────────────────────────────

CATS = {
    "ai-agents-llm": {
        "name": "🤖 AI AGENTS & LLM",
        "desc": "Multi-agent frameworks, agent orchestration, LLM fine-tuning and infrastructure.",
    },
    "rag-knowledge": {
        "name": "🧠 RAG & KNOWLEDGE BASE",
        "desc": "Retrieval-Augmented Generation, vector search, knowledge graphs and context engineering.",
    },
    "python-tools": {
        "name": "🐍 PYTHON TOOLS & DATA",
        "desc": "Python ecosystem, data processing, ML/AI libraries, Jupyter notebooks.",
    },
    "web-ui": {
        "name": "🌐 WEB & UI",
        "desc": "Next.js, React, TypeScript, browser automation, CSS/UI frameworks.",
    },
    "dev-infra": {
        "name": "⚙️  DEV INFRA & TOOLING",
        "desc": "CLI tools, GitHub Actions, Docker, Kubernetes, shell scripts, developer infrastructure.",
    },
    "rust-systems": {
        "name": "🔧 RUST & SYSTEMS",
        "desc": "Rust ecosystem, browser engines, database engines, performance tooling.",
    },
    "data-analytics": {
        "name": "📊 DATA & ANALYTICS",
        "desc": "Dashboards, data pipelines, BI tools, analytics and visualization.",
    },
    "cloud-deploy": {
        "name": "☁️  CLOUD & DEPLOY",
        "desc": "AWS, GCP, Azure, serverless, Kubernetes, infrastructure-as-code.",
    },
}

# ── Keyword Maps ─────────────────────────────────────────────────────────────

AI_KWDS     = ['llm','ai-agent','ai-agents','agent','agents','agentic','claude-code','anthropic','openai','gemini','deepseek','llama','mistral','gpt','localai','ollama','mcp','hermes','autonomous','swarm','multi-agent','nous-research','anthropic-claude']
RAG_KWDS    = ['rag','retrieval','vector','embed','knowledge-base','knowledge-graph','chunking','context-engineering']
PY_KWDS     = ['python','data','pandas','numpy','jupyter','notebook','scraping','crawl','etl','pipeline']
WEB_KWDS    = ['nextjs','react','typescript','javascript','css','html','frontend','ui','web','browser','playwright']
DEV_KWDS    = ['cli','tool','github-action','docker','kubernetes','k8s','shell','bash','git','devops','cicd','infrastructure','deploy','build','automation']
RUST_KWDS   = ['rust','systems','engine','performance','browser-engine','database','embedded']
DATA_KWDS   = ['analytics','dashboard','visualization','metrics','logging','monitoring','bi','statistics']
CLOUD_KWDS  = ['aws','azure','gcp','cloud','serverless','lambda','terraform']


def get_token():
    token = os.environ.get('GH_TOKEN')
    if not token:
        # Try to get from gh CLI
        try:
            token = subprocess.check_output(['gh', 'auth', 'token'], text=True).strip()
        except Exception:
            raise SystemExit("GH_TOKEN not set and `gh auth token` failed")
    return token


def fetch_stars(token):
    """Fetch all starred repos via GitHub API (paginated)."""
    import urllib.request
    import time

    repos = []
    page = 1
    per_page = 100
    max_retries = 3

    while True:
        url = f"https://api.github.com/user/starred?per_page={per_page}&page={page}&sort=updated"
        req = urllib.request.Request(url, headers={
            'Authorization': f'token {token}',
            'Accept': 'application/vnd.github+json',
            'X-GitHub-Api-Version': '2022-11-28',
            'User-Agent': 'starz-sync/1.0'
        })

        for attempt in range(max_retries):
            try:
                with urllib.request.urlopen(req, timeout=30) as resp:
                    data = json.loads(resp.read())
                    if not data:
                        return repos
                    repos.extend(data)
                if len(data) < per_page:
                    return repos
                break
            except urllib.error.HTTPError as e:
                if e.code == 401:
                    raise SystemExit(f"GitHub API returned 401 Unauthorized — check that STARZ_PAT is valid and not expired. Details: {e}")
                if e.code == 403 and 'rate limit' in str(e).lower():
                    print(f"   ⚠️  Rate limited, waiting 60s...")
                    time.sleep(60)
                    continue
                if attempt == max_retries - 1:
                    raise SystemExit(f"GitHub API error after {max_retries} retries: HTTP {e.code} — {e}")
                print(f"   ⚠️  HTTP {e.code}, retrying ({attempt + 1}/{max_retries})...")
                time.sleep(5)
            except Exception as e:
                if attempt == max_retries - 1:
                    raise SystemExit(f"Failed to fetch stars after {max_retries} retries: {e}")
                print(f"   ⚠️  {e}, retrying ({attempt + 1}/{max_retries})...")
                time.sleep(5)

        page += 1

    return repos


def categorize(r):
    lang   = (r.get('language') or '').lower()
    topics = r.get('topics') or []
    desc   = (r.get('description') or '').lower()
    t = ' '.join(topics + [lang, desc])

    if any(k in t for k in RAG_KWDS):  return "rag-knowledge"
    if any(k in t for k in AI_KWDS):   return "ai-agents-llm"
    if 'python' in lang or any(k in t for k in PY_KWDS):  return "python-tools"
    if lang in ['typescript', 'javascript', 'html']:       return "web-ui"
    if 'rust' in lang:                return "rust-systems"
    if any(k in t for k in DATA_KWDS): return "data-analytics"
    if any(k in t for k in CLOUD_KWDS): return "cloud-deploy"
    if any(k in t for k in DEV_KWDS): return "dev-infra"
    if lang in ['python', 'jupyter notebook']: return "python-tools"
    if lang in ['typescript', 'javascript']:  return "web-ui"
    return "dev-infra"


def slug(name):
    """Safe folder name from repo name."""
    return name.replace('.', '-').replace('_', '-')


def write_readme(path, content):
    with open(path, 'w') as f:
        f.write(content)


def main():
    print("🔄 Fetching stars from GitHub...")
    token = get_token()
    repos = fetch_stars(token)
    print(f"   → {len(repos)} starred repos found")

    cat_repos = {k: [] for k in CATS}
    for r in repos:
        cat_repos[categorize(r)].append(r)

    # ── Main README ──────────────────────────────────────────────────────────
    main_readme = f"""# ⭐ STARZ

> Your {len(repos)} starred GitHub repositories, organized into {len(CATS)} categories.

*"A library is a collection of adventures you haven't had yet."*

---

## 📂 Categories

| # | Category | Count |
|---|----------|-------|
| 1 | {CATS['ai-agents-llm']['name']} | {len(cat_repos['ai-agents-llm'])} |
| 2 | {CATS['rag-knowledge']['name']} | {len(cat_repos['rag-knowledge'])} |
| 3 | {CATS['python-tools']['name']} | {len(cat_repos['python-tools'])} |
| 4 | {CATS['web-ui']['name']} | {len(cat_repos['web-ui'])} |
| 5 | {CATS['dev-infra']['name']} | {len(cat_repos['dev-infra'])} |
| 6 | {CATS['rust-systems']['name']} | {len(cat_repos['rust-systems'])} |
| 7 | {CATS['data-analytics']['name']} | {len(cat_repos['data-analytics'])} |
| 8 | {CATS['cloud-deploy']['name']} | {len(cat_repos['cloud-deploy'])} |

---

## 🗂️ Index files (auto-generated, local)

| File | What | Use |
|------|------|-----|
| [`INDEX.md`](./INDEX.md) | Master table of all repos by stars | Grep for a repo; read for the landscape |
| [`TOPICS.md`](./TOPICS.md) | Reverse index: topic → repos | Grep by subject (`grpo`, `rag`, `finance`) |

Regenerated by `build_index.py` after every sync — no API calls.

*Maintained by [@saidrassai](https://github.com/saidrassai) · Auto-synced daily*
"""
    write_readme(REPO_DIR / 'README.md', main_readme)

    # ── Category folders ────────────────────────────────────────────────────
    for slug_cat, info in CATS.items():
        cat_dir   = REPO_DIR / slug_cat
        readme_dir = cat_dir / 'readme'
        readme_dir.mkdir(parents=True, exist_ok=True)

        # Category README
        cat_readme = f"""# {info['name']}

{info['desc']}

**Total: {len(cat_repos[slug_cat])} repos**

---

## 📋 Repositories

| # | Repository | Language | Description |
|---|-----------|----------|-------------|
"""
        repos_sorted = sorted(cat_repos[slug_cat], key=lambda x: x['full_name'].lower())
        for i, r in enumerate(repos_sorted, 1):
            lang = r.get('language') or '—'
            desc = (r.get('description') or '—').replace('|', '\\|').replace('\n', ' ')[:100]
            cat_readme += f"| {i} | [{r['full_name']}](https://github.com/{r['full_name']}) | {lang} | {desc} |\n"

        cat_readme += f"\n---\n*Auto-generated by [starz](https://github.com/saidrassai/starz)*\n"
        write_readme(cat_dir / 'README.md', cat_readme)

        # Individual repo subfolders
        for r in repos_sorted:
            owner, name = r['full_name'].split('/')
            repo_dir = cat_dir / name
            repo_dir.mkdir(parents=True, exist_ok=True)

            topics  = ', '.join(r.get('topics') or []) or 'No topics'
            desc    = r.get('description') or 'No description available.'
            lang    = r.get('language') or '—'
            stars   = r.get('stargazers_count', '?')
            forks   = r.get('forks_count', '?')
            lic     = r.get('license', {})
            lic     = lic.get('name', 'Not specified') if isinstance(lic, dict) else 'Not specified'

            readme_content = f"""# ⭐ {r['full_name']}

{desc}

## 📌 Quick Info

| Field | Value |
|-------|-------|
| **Language** | {lang} |
| **Stars** | {stars} |
| **Forks** | {forks} |
| **License** | {lic} |

## 🏷️ Topics

{topics}

## 🔗 Links

- 🌐 [View on GitHub](https://github.com/{r['full_name']})

---
*Added via [starz](https://github.com/saidrassai/starz) · [@saidrassai](https://github.com/saidrassai)*
"""
            write_readme(repo_dir / 'README.md', readme_content)

        print(f"✅ {info['name']}: {len(cat_repos[slug_cat])} repos")

    print(f"\n✅ Done — {len(repos)} repos across {len(CATS)} categories")


if __name__ == '__main__':
    main()
