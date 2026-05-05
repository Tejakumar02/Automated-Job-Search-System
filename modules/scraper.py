"""
modules/scraper.py
Job discovery using python-jobspy (zero-cost, no login required).
Scrapes LinkedIn, Indeed, Glassdoor, Google Jobs, Naukri.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


import time
import yaml
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [SCRAPER] %(message)s")
log = logging.getLogger(__name__)


def load_config():
    with open("config/config.yaml") as f:
        return yaml.safe_load(f)


def scrape_jobs(search_term: str, location: str, results: int = 30) -> list[dict]:
    """
    Scrape jobs for a single search term from multiple platforms.
    Uses python-jobspy under the hood.
    """
    try:
        from jobspy import scrape_jobs as _scrape
    except ImportError:
        log.error("python-jobspy not installed. Run: pip install python-jobspy")
        return []

    try:
        log.info(f"🔍 Scraping: '{search_term}' in {location}")
        df = _scrape(
            site_name=["linkedin", "indeed", "glassdoor", "google"],
            search_term=search_term,
            location=location,
            results_wanted=results,
            hours_old=24,           # Only last 24 hours
            country_indeed="India",
            linkedin_fetch_description=True,
            verbose=0,
        )
        if df is None or df.empty:
            log.warning(f"No results for '{search_term}'")
            return []

        jobs = []
        for _, row in df.iterrows():
            job = {
                "title":       str(row.get("title", "") or ""),
                "company":     str(row.get("company", "") or ""),
                "location":    str(row.get("location", "") or ""),
                "url":         str(row.get("job_url", "") or ""),
                "source":      str(row.get("site", "") or ""),
                "description": str(row.get("description", "") or ""),
                "date_posted": str(row.get("date_posted", "") or ""),
            }
            jobs.append(job)

        log.info(f"✅ Found {len(jobs)} jobs for '{search_term}'")
        return jobs

    except Exception as e:
        log.error(f"Scraping failed for '{search_term}': {e}")
        return []


def scrape_naukri(search_term: str, location: str = "Chennai") -> list[dict]:
    """
    Naukri fallback scraper using requests + BeautifulSoup.
    Scrapes public search results without login.
    """
    import requests
    from bs4 import BeautifulSoup

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "en-US,en;q=0.9",
    }

    query = search_term.replace(" ", "-").lower()
    loc   = location.lower()
    url   = f"https://www.naukri.com/{query}-jobs-in-{loc}?experience=0"

    try:
        resp = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(resp.text, "html.parser")
        jobs = []

        # Naukri job cards
        cards = soup.select("article.jobTuple")
        for card in cards[:20]:
            title   = card.select_one("a.title")
            company = card.select_one("a.subTitle")
            job_url = title["href"] if title and title.has_attr("href") else ""
            desc_el = card.select_one("ul.tags")
            desc    = desc_el.get_text(" | ") if desc_el else ""

            if title:
                jobs.append({
                    "title":       title.get_text(strip=True),
                    "company":     company.get_text(strip=True) if company else "",
                    "location":    location,
                    "url":         job_url,
                    "source":      "naukri",
                    "description": desc,
                    "date_posted": "",
                })

        log.info(f"[Naukri] Found {len(jobs)} jobs for '{search_term}'")
        return jobs

    except Exception as e:
        log.error(f"[Naukri] Scraping failed: {e}")
        return []


def run_full_scrape() -> list[dict]:
    """
    Run scraping for all target roles and combine results.
    Deduplicates by URL before returning.
    """
    cfg = load_config()
    roles    = cfg["target_roles"]
    location = cfg["job_search"]["location"]
    n        = cfg["job_search"]["results_per_site"]

    all_jobs = []
    seen_urls = set()

    locations = cfg["job_search"].get("locations", [location])

    for role in roles:
        for loc in locations:
            # Main scraper (LinkedIn, Indeed, Glassdoor, Google)
            jobs = scrape_jobs(role, loc, results=n)
            time.sleep(2)   # Polite delay between requests

        # Naukri supplemental
        naukri_locations=["Chennai", "Bangalore", "Hyderabad", "Remote", "Bengaluru"]
        for nloc in naukri_locations:
            naukri_jobs = scrape_naukri(role, location=nloc)
            time.sleep(1)

        for job in jobs + naukri_jobs:
            url = job.get("url", "")
            if url and url not in seen_urls:
                seen_urls.add(url)
                all_jobs.append(job)

    log.info(f"📦 Total unique jobs collected: {len(all_jobs)}")
    return all_jobs


if __name__ == "__main__":
    jobs = run_full_scrape()
    for j in jobs[:5]:
        print(f"  • {j['title']} @ {j['company']} [{j['source']}]")
