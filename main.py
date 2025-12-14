import os
import base64
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Optional

import requests
from fastapi import FastAPI
from pydantic import BaseModel
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware



# Load environment variables
load_dotenv()
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

# FastAPI app
app = FastAPI(title="Repository Mirror", version="1.0.0")

# Enable CORS (important for frontend integration)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Homepage route
@app.get("/")
def home():
    return {"message": "Repository Mirror API is running 🚀"}

# Input model
class RepoInput(BaseModel):
    url: str

# GitHub headers
def gh_headers() -> Dict[str, str]:
    headers = {"Accept": "application/vnd.github+json"}
    if GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"
    return headers

# Parse repo URL
def parse_owner_repo(repo_url: str) -> Optional[Dict[str, str]]:
    try:
        parts = repo_url.strip("/").split("/")
        idx = parts.index("github.com")
        owner, repo = parts[idx + 1], parts[idx + 2]
        return {"owner": owner, "repo": repo}
    except Exception:
        return None
def assign_tier(total_score: float) -> Dict[str, str]:
    if total_score >= 80:
        return {"tier": "Gold", "badge": "🥇"}
    elif total_score >= 60:
        return {"tier": "Silver", "badge": "🥈"}
    else:
        return {"tier": "Bronze", "badge": "🥉"}

# Safe GET request
def safe_get(url: str) -> Optional[requests.Response]:
    try:
        resp = requests.get(url, headers=gh_headers(), timeout=15)
        if resp.status_code == 200:
            return resp
        return None
    except Exception:
        return None

# GitHub API fetchers
def fetch_repo_core(owner: str, repo: str) -> Dict[str, Any]:
    core = safe_get(f"https://api.github.com/repos/{owner}/{repo}")
    return core.json() if core else {}

def fetch_readme(owner: str, repo: str) -> Dict[str, Any]:
    resp = safe_get(f"https://api.github.com/repos/{owner}/{repo}/readme")
    if not resp:
        return {"present": False, "length": 0, "content_preview": ""}
    data = resp.json()
    content = ""
    try:
        if data.get("encoding") == "base64":
            content = base64.b64decode(data.get("content", "")).decode(errors="ignore")
        else:
            raw = safe_get(data.get("download_url", ""))
            content = raw.text if raw else ""
    except Exception:
        content = ""
    return {
        "present": True,
        "length": len(content),
        "lines_count": len(content.splitlines()),
        "has_sections": any(h in content.lower() for h in ["installation", "usage", "contributing", "license"]),
        "has_code_block": "```" in content,
        "content_preview": content[:400],
    }

def fetch_languages(owner: str, repo: str) -> Dict[str, int]:
    resp = safe_get(f"https://api.github.com/repos/{owner}/{repo}/languages")
    return resp.json() if resp else {}

def fetch_contents(owner: str, repo: str, path: str = "") -> List[Dict[str, Any]]:
    resp = safe_get(f"https://api.github.com/repos/{owner}/{repo}/contents/{path}")
    return resp.json() if resp else []

def fetch_commits(owner: str, repo: str, per_page: int = 100) -> List[Dict[str, Any]]:
    resp = safe_get(f"https://api.github.com/repos/{owner}/{repo}/commits?per_page={per_page}")
    return resp.json() if resp else []

def fetch_branches(owner: str, repo: str) -> List[Dict[str, Any]]:
    resp = safe_get(f"https://api.github.com/repos/{owner}/{repo}/branches")
    return resp.json() if resp else []

def fetch_pulls(owner: str, repo: str, state: str = "all") -> List[Dict[str, Any]]:
    resp = safe_get(f"https://api.github.com/repos/{owner}/{repo}/pulls?state={state}")
    return resp.json() if resp else []

# Analysis helpers
def analyze_structure(root_contents: List[Dict[str, Any]]) -> Dict[str, Any]:
    filenames = [item.get("name", "").lower() for item in root_contents]
    return {
        "has_tests_folder": any(n in filenames for n in ["tests", "test"]),
        "has_src_folder": any(n in filenames for n in ["src", "app"]),
        "has_ci": any(n in filenames for n in [".github", ".gitlab-ci.yml"]),
        "has_license": any(n in filenames for n in ["license", "license.md"]),
        "has_contributing": any(n in filenames for n in ["contributing.md"]),
        "readme_present": any(n in filenames for n in ["readme.md", "readme"]),
        "files_count_root": len(root_contents),
    }
def analyze_commits(commits: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not commits:
        return {"count": 0, "recent_activity": False, "message_quality_ratio": 0.0}
    dates = []
    good_message = 0
    for c in commits:
        msg = (c.get("commit", {}).get("message", "") or "").strip()
        if any(tag in msg.lower() for tag in ["fix", "feat", "refactor"]):
            good_message += 1
        date_str = c.get("commit", {}).get("author", {}).get("date", "")
        try:
            # Parse ISO date string into offset-aware datetime
            dates.append(datetime.fromisoformat(date_str.replace("Z", "+00:00")))
        except Exception:
            continue
    
    # Use timezone-aware UTC now
    recent_activity = max(dates) >= datetime.now(timezone.utc) - timedelta(days=30) if dates else False
    
    return {
        "count": len(commits),
        "recent_activity": recent_activity,
        "message_quality_ratio": round(good_message / max(1, len(commits)), 2),
    }



def analyze_readme_quality(readme: Dict[str, Any]) -> float:
    if not readme.get("present"):
        return 0.0
    score = 0.0
    if readme.get("length", 0) > 400: score += 0.4
    if readme.get("has_sections"): score += 0.3
    if readme.get("has_code_block"): score += 0.2
    if readme.get("lines_count", 0) > 20: score += 0.1
    return min(score, 1.0)

def analyze_version_control(branches: List[Dict[str, Any]], pulls: List[Dict[str, Any]]) -> float:
    score = 0.0
    if len(branches) >= 2: score += 0.5
    if len(pulls) >= 1: score += 0.5
    return min(score, 1.0)

def analyze_test_presence(structure: Dict[str, Any]) -> float:
    return 1.0 if structure.get("has_tests_folder") else 0.0

# Scoring
def compute_score(readme_q: float, commits_q: Dict[str, Any], vc_q: float, structure_q: Dict[str, Any]) -> Dict[str, Any]:
    doc_score = readme_q * 100
    commit_score = commits_q.get("message_quality_ratio", 0.0) * 100
    vc_score = vc_q * 100
    structure_score = sum([
        20 if structure_q.get("readme_present") else 0,
        25 if structure_q.get("has_src_folder") else 0,
        20 if structure_q.get("has_ci") else 0,
        20 if structure_q.get("has_license") else 0,
        15 if structure_q.get("has_contributing") else 0,
    ])
    test_score = analyze_test_presence(structure_q) * 100
    total = round((doc_score + commit_score + vc_score + structure_score + test_score) / 5, 1)
    return {
        "total": total,
        "breakdown": {
            "documentation": round(doc_score, 1),
            "commit_consistency": round(commit_score, 1),
            "version_control": round(vc_score, 1),
            "structure": round(structure_score, 1),
            "tests": round(test_score, 1),
        },
    }

# Summary & Roadmap
def generate_summary(score: Dict[str, Any]) -> str:
    return f"Overall score: {score['total']} with strengths in {', '.join([k for k,v in score['breakdown'].items() if v>=60])}."

def generate_roadmap(score: Dict[str, Any]) -> List[str]:
    roadmap = []
    
    if score["breakdown"]["documentation"] < 70:
        roadmap.append("Add a comprehensive README with Installation, Usage, and Contributing sections, plus code examples.")
    
    if score["breakdown"]["tests"] < 70:
        roadmap.append("Add a tests/ folder and write unit tests for critical modules; include coverage reporting.")
    
    if score["breakdown"]["version_control"] < 70:
        roadmap.append("Adopt a branching strategy (feature branches) and use pull requests for code review.")
    
    if score["breakdown"]["structure"] < 70:
        roadmap.append("Refactor into a clear src/ hierarchy and add CI via GitHub Actions for linting and tests.")
    
    if score["breakdown"]["commit_consistency"] < 70:
        roadmap.append("Improve commit frequency and write descriptive commit messages (e.g., feat:, fix:, refactor:).")
    
    # License check
    if score["breakdown"]["structure"] < 70 and not score["breakdown"].get("license", 0):
        roadmap.append("Add a LICENSE file (MIT/Apache-2.0) to clarify usage.")
    
    # Contributing check
    if score["breakdown"]["structure"] < 70 and not score["breakdown"].get("contributing", 0):
        roadmap.append("Add a CONTRIBUTING.md to guide collaborators.")
    
    return roadmap
@app.post("/analyze")
def analyze_repo(input: RepoInput) -> Dict[str, Any]:
    parsed = parse_owner_repo(input.url)
    if not parsed:
        return {"error": "Invalid GitHub URL"}

    owner, repo = parsed["owner"], parsed["repo"]

    # Fetch data
    core = fetch_repo_core(owner, repo)
    readme = fetch_readme(owner, repo)
    languages = fetch_languages(owner, repo)
    contents = fetch_contents(owner, repo)
    commits = fetch_commits(owner, repo)
    branches = fetch_branches(owner, repo)
    pulls = fetch_pulls(owner, repo)

    # Analyze
    structure_q = analyze_structure(contents)
    commits_q = analyze_commits(commits)
    readme_q = analyze_readme_quality(readme)
    vc_q = analyze_version_control(branches, pulls)
    score = compute_score(readme_q, commits_q, vc_q, structure_q)

    # Assign tier
    tier_info = assign_tier(score["total"])

    # Build response
    return {
        "score": score,
        "tier": tier_info,   # 👈 Added here
        "summary": generate_summary(score),
        "roadmap": generate_roadmap(score),
        "languages": languages,
        "readme_preview": readme.get("content_preview", ""),
    }
