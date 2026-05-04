"""
main.py
Central orchestrator for the Job Search Assistant.
Runs the full pipeline and schedules twice-daily at 12:00 PM & 8:00 PM IST.

Usage:
    python main.py            # Start the scheduler (runs forever)
    python main.py --now      # Run immediately once
    python main.py --test     # Send test notification only
    python main.py --status   # Show database stats
    python main.py --setup    # First-time setup check
"""

import sys, os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
sys.path.insert(0, os.path.abspath('.'))

import time
import yaml
import logging
import argparse
from pathlib import Path
from datetime import datetime
import schedule

# ── Ensure project root is on the path (fixes Windows ModuleNotFoundError) ────
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# ── Local modules ──────────────────────────────────────────────────────────────
from modules.database     import init_db, insert_job, get_unnotified_jobs, mark_notified, log_run, get_stats, update_status
from modules.scraper      import run_full_scrape
from modules.filter_score import filter_and_rank
from modules.resume_tailor import process_job_resume
from modules.notifier     import notify_all, send_test_notification

# ── Logging ────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("logs/job_assistant.log", encoding="utf-8"),
    ],
)
log = logging.getLogger("MAIN")


def load_config():
    with open("config/config.yaml") as f:
        return yaml.safe_load(f)


# ─── Full Pipeline ─────────────────────────────────────────────────────────────

def run_pipeline():
    """
    Complete job search pipeline:
    1. Scrape jobs from all platforms
    2. Filter + score for fresher relevance
    3. Save new jobs to SQLite (deduplication)
    4. Tailor resume for each top job (via Ollama)
    5. Notify via Telegram + Email
    """
    start_time = datetime.now()
    log.info("=" * 60)
    log.info(f"🚀 Pipeline started at {start_time.strftime('%d %b %Y %I:%M %p IST')}")
    log.info("=" * 60)

    # Step 1: Scrape ────────────────────────────────────────────────
    log.info("📡 Step 1/5 — Scraping jobs from all platforms...")
    raw_jobs = run_full_scrape()
    log.info(f"   → Collected {len(raw_jobs)} raw jobs")

    # Step 2: Filter + Rank ─────────────────────────────────────────
    log.info("🔍 Step 2/5 — Filtering and scoring jobs...")
    top_jobs = filter_and_rank(raw_jobs)
    log.info(f"   → {len(top_jobs)} jobs passed filter")

    if not top_jobs:
        log.info("   ℹ️  No qualifying jobs found this run.")
        log_run(len(raw_jobs), 0, 0)
        return

    # Step 3: Save to DB ────────────────────────────────────────────
    log.info("💾 Step 3/5 — Saving new jobs to database...")
    new_count = 0
    for job in top_jobs:
        if insert_job(job):
            new_count += 1

    log.info(f"   → {new_count} new unique jobs saved (duplicates skipped)")

    # Step 4: Tailor Resumes ────────────────────────────────────────
    log.info("🤖 Step 4/5 — Tailoring resumes with Ollama LLM...")
    jobs_to_notify = get_unnotified_jobs(limit=15)

    for job in jobs_to_notify:
        try:
            resume_paths = process_job_resume(job)
            if resume_paths.get("pdf"):
                update_status(job["id"], "new", resume_paths.get("pdf"))
                log.info(f"   ✅ Resume ready for: {job['title']} @ {job['company']}")
        except Exception as e:
            log.warning(f"   ⚠️  Resume tailor failed for {job['title']}: {e}")

    # Step 5: Notify ────────────────────────────────────────────────
    log.info("📬 Step 5/5 — Sending notifications...")
    notif_results = notify_all(jobs_to_notify)
    mark_notified([j["id"] for j in jobs_to_notify])

    # Log run to DB
    log_run(len(raw_jobs), new_count, len(jobs_to_notify))

    elapsed = (datetime.now() - start_time).seconds
    log.info("─" * 60)
    log.info(f"✅ Pipeline complete in {elapsed}s")
    log.info(f"   Scraped: {len(raw_jobs)} | New: {new_count} | Notified: {len(jobs_to_notify)}")
    log.info(f"   Telegram: {'✅' if notif_results.get('telegram') else '❌'}")
    log.info(f"   Email:    {'✅' if notif_results.get('email') else '❌'}")
    log.info("─" * 60)


# ─── Setup Check ──────────────────────────────────────────────────────────────

def setup_check():
    """Verify all dependencies and config before first run."""
    import importlib
    print("\n" + "=" * 50)
    print("  🔧  Job Search Assistant — Setup Check")
    print("=" * 50)

    checks = {
        "jobspy":       "python-jobspy",
        "requests":     "requests",
        "bs4":          "beautifulsoup4",
        "schedule":     "schedule",
        "yaml":         "pyyaml",
        "markdown":     "markdown",
    }

    all_ok = True
    for module, pkg in checks.items():
        try:
            importlib.import_module(module)
            print(f"  ✅ {pkg}")
        except ImportError:
            print(f"  ❌ {pkg}  →  pip install {pkg}")
            all_ok = False

    # Check Ollama
    import subprocess
    try:
        r = subprocess.run(["ollama", "list"], capture_output=True, timeout=5)
        print("  ✅ Ollama installed")
        if b"llama3" in r.stdout or b"qwen" in r.stdout:
            print("  ✅ LLM model found")
        else:
            print("  ⚠️  No model found  →  ollama pull llama3.1")
    except Exception:
        print("  ❌ Ollama not found  →  https://ollama.ai")
        all_ok = False

    # Check pandoc
    try:
        subprocess.run(["pandoc", "--version"], capture_output=True, timeout=5)
        print("  ✅ pandoc installed")
    except Exception:
        print("  ⚠️  pandoc not found  →  sudo apt install pandoc")

    # Check master resume
    cfg = load_config()
    if Path(cfg["resumes"]["master_resume"]).exists():
        print("  ✅ Master resume found")
    else:
        print(f"  ⚠️  Create: {cfg['resumes']['master_resume']}")

    print("=" * 50)
    if all_ok:
        print("  🚀 All checks passed! Run: python main.py --now")
    else:
        print("  ⚠️  Fix the above issues then retry.")
    print()


# ─── Scheduler ────────────────────────────────────────────────────────────────

def start_scheduler():
    """
    Schedule twice-daily runs at 12:00 PM and 8:00 PM IST.
    Note: Run on a machine with IST timezone or adjust times accordingly.
    """
    cfg   = load_config()
    times = cfg["job_search"]["schedule_times"]   # ["12:00", "20:00"]

    for t in times:
        schedule.every().day.at(t).do(run_pipeline)
        log.info(f"⏰ Scheduled daily run at {t} IST")

    log.info("🕐 Scheduler started. Press Ctrl+C to stop.")
    log.info(f"   Next runs: {[j.next_run for j in schedule.jobs]}")

    while True:
        schedule.run_pending()
        time.sleep(30)


# ─── CLI Entry ─────────────────────────────────────────────────────────────────

def main():
    from pathlib import Path
    Path("logs").mkdir(exist_ok=True)
    init_db()

    parser = argparse.ArgumentParser(description="Job Search Assistant")
    parser.add_argument("--now",    action="store_true", help="Run pipeline immediately")
    parser.add_argument("--test",   action="store_true", help="Send test notification")
    parser.add_argument("--status", action="store_true", help="Show database stats")
    parser.add_argument("--setup",  action="store_true", help="Run setup check")
    args = parser.parse_args()

    if args.setup:
        setup_check()
    elif args.test:
        send_test_notification()
    elif args.status:
        stats = get_stats()
        print("\n📊 Job Tracker Stats")
        print(f"   Total jobs tracked : {stats['total']}")
        print(f"   Applied            : {stats['applied']}")
        print(f"   New (not applied)  : {stats['new']}")
        print(f"   Skipped            : {stats['skipped']}\n")
    elif args.now:
        run_pipeline()
    else:
        # Default: start scheduler
        start_scheduler()


if __name__ == "__main__":
    main()
