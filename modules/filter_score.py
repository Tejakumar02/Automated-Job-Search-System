"""
modules/filter_score.py
Filter jobs to fresher-friendly roles and score them
based on skill match, title relevance, and recency.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


import re
import yaml
from datetime import datetime, timedelta
from typing import Optional
import logging

log = logging.getLogger(__name__)


def load_config():
    with open("config/config.yaml") as f:
        return yaml.safe_load(f)


# ─── Fresher Filter ───────────────────────────────────────────────────────────

def is_fresher_friendly(job: dict, cfg: dict) -> bool:
    """
    Return True if the job is likely suitable for a fresher.
    Checks title + description against include/exclude keyword lists.
    """
    text = (
        (job.get("title", "") + " " + job.get("description", ""))
        .lower()
    )

    # Hard exclude — if any exclusion keyword is found, reject
    for kw in cfg["filtering"]["exclude_keywords"]:
        if re.search(rf"\b{re.escape(kw.lower())}\b", text):
            return False

    # Must contain at least ONE include keyword OR title must match target roles
    target_titles = [r.lower() for r in cfg["target_roles"]]
    title_lower   = job.get("title", "").lower()

    title_match = any(t in title_lower for t in target_titles)
    kw_match    = any(
        re.search(rf"\b{re.escape(kw.lower())}\b", text)
        for kw in cfg["filtering"]["include_keywords"]
    )

    return title_match or kw_match


# ─── Scoring ──────────────────────────────────────────────────────────────────

SKILL_SYNONYMS = {
    "python":           ["python", "py"],
    "machine learning": ["machine learning", "ml", "sklearn", "scikit"],
    "deep learning":    ["deep learning", "dl", "neural network", "cnn", "rnn", "transformer"],
    "computer vision":  ["computer vision", "cv", "opencv", "image processing", "yolo", "detectron"],
    "ai":               ["artificial intelligence", "ai", "llm", "nlp", "generative"],
    "data science":     ["data science", "data analysis", "pandas", "numpy", "matplotlib"],
    "automation":       ["automation", "selenium", "pytest", "rpa", "airflow"],
    "pytorch":          ["pytorch", "torch"],
    "tensorflow":       ["tensorflow", "keras", "tf"],
}

TARGET_TITLE_KEYWORDS = [
    "ai", "ml", "machine learning", "deep learning", "computer vision",
    "python", "data scientist", "automation", "graduate trainee",
    "associate engineer", "junior engineer",
]


def score_skill_match(text: str, skills: list[str]) -> float:
    """
    Score 0–100 based on how many candidate skills appear in the JD.
    """
    text_lower = text.lower()
    matched    = 0
    total      = len(SKILL_SYNONYMS)

    for skill_key, synonyms in SKILL_SYNONYMS.items():
        if any(s in text_lower for s in synonyms):
            matched += 1

    return round((matched / total) * 100, 1)


def score_title_match(title: str) -> float:
    """
    Score 0–100 based on how well the job title aligns with target roles.
    """
    title_lower = title.lower()
    hits = sum(1 for kw in TARGET_TITLE_KEYWORDS if kw in title_lower)
    return min(round((hits / 3) * 100, 1), 100)   # cap at 100


def score_recency(date_posted: str) -> float:
    """
    Score 0–100. Jobs posted today = 100, older = lower.
    """
    if not date_posted:
        return 50   # Unknown date → neutral

    try:
        # Handle various date formats
        for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%B %d, %Y", "%Y-%m-%dT%H:%M:%S"):
            try:
                posted = datetime.strptime(str(date_posted)[:10], fmt[:len(fmt)])
                break
            except ValueError:
                continue
        else:
            return 50

        days_old = (datetime.now() - posted).days
        if days_old <= 0:   return 100
        if days_old <= 1:   return 90
        if days_old <= 3:   return 70
        if days_old <= 7:   return 50
        if days_old <= 14:  return 30
        return 10

    except Exception:
        return 50


def compute_score(job: dict, cfg: dict) -> float:
    """
    Weighted final score for a job (0–100).
    Weights are configured in config.yaml.
    """
    text       = job.get("description", "") + " " + job.get("title", "")
    skills     = cfg["candidate"]["skills"]
    w          = cfg["scoring"]

    skill_score  = score_skill_match(text, skills)
    title_score  = score_title_match(job.get("title", ""))
    recent_score = score_recency(job.get("date_posted", ""))

    final = (
        skill_score  * (w["skill_match_weight"] / 100) +
        title_score  * (w["title_match_weight"]  / 100) +
        recent_score * (w["recency_weight"]       / 100)
    )
    return round(final, 1)


# ─── Main Filter + Rank ───────────────────────────────────────────────────────

def filter_and_rank(jobs: list[dict]) -> list[dict]:
    """
    Filter jobs to fresher-friendly ones, score them,
    and return the top-N ranked list.
    """
    cfg = load_config()
    min_score = cfg["filtering"]["min_score"]
    top_n     = cfg["filtering"]["top_n"]

    filtered = []
    for job in jobs:
        if not is_fresher_friendly(job, cfg):
            continue

        score = compute_score(job, cfg)
        if score < min_score:
            continue

        job["score"] = score
        filtered.append(job)

    # Sort by score descending
    ranked = sorted(filtered, key=lambda x: x["score"], reverse=True)
    top    = ranked[:top_n]

    log.info(
        f"[Filter] {len(jobs)} scraped → "
        f"{len(filtered)} passed filter → "
        f"{len(top)} selected (top {top_n})"
    )
    return top


if __name__ == "__main__":
    # Quick test
    sample = [
        {
            "title": "Junior ML Engineer",
            "company": "TechCorp",
            "description": "We need a Python developer with machine learning skills. Fresher welcome. 0-2 years.",
            "date_posted": datetime.now().strftime("%Y-%m-%d"),
            "url": "https://example.com/job/1",
            "source": "linkedin",
        },
        {
            "title": "Senior Data Scientist",
            "company": "BigCo",
            "description": "7+ years experience required. Lead a team.",
            "date_posted": "2024-01-01",
            "url": "https://example.com/job/2",
            "source": "indeed",
        },
    ]
    results = filter_and_rank(sample)
    for r in results:
        print(f"  ✅ [{r['score']}] {r['title']} @ {r['company']}")
