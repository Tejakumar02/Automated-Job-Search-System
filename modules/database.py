"""
modules/database.py
SQLite-based job tracking — stores jobs, prevents duplicates,
tracks application status.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


import sqlite3
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Optional
import yaml


def load_config():
    with open("config/config.yaml") as f:
        return yaml.safe_load(f)


def get_connection() -> sqlite3.Connection:
    cfg = load_config()
    db_path = Path(cfg["database"]["path"])
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create tables if they don't exist."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS jobs (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            job_hash        TEXT UNIQUE NOT NULL,
            title           TEXT NOT NULL,
            company         TEXT NOT NULL,
            location        TEXT,
            url             TEXT,
            source          TEXT,
            description     TEXT,
            score           REAL DEFAULT 0,
            date_discovered TEXT,
            date_posted     TEXT,
            status          TEXT DEFAULT 'new',
            resume_path     TEXT,
            notified        INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS run_log (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            run_time    TEXT,
            jobs_found  INTEGER,
            jobs_new    INTEGER,
            jobs_notified INTEGER
        );
    """)
    conn.commit()
    conn.close()
    print("[DB] ✅ Database initialised.")


def make_hash(title: str, company: str, url: str = "") -> str:
    """Unique hash per job to detect duplicates."""
    raw = f"{title.lower().strip()}|{company.lower().strip()}|{url.strip()}"
    return hashlib.md5(raw.encode()).hexdigest()


def job_exists(job_hash: str) -> bool:
    conn = get_connection()
    row = conn.execute(
        "SELECT 1 FROM jobs WHERE job_hash = ?", (job_hash,)
    ).fetchone()
    conn.close()
    return row is not None


def insert_job(job: dict) -> bool:
    """
    Insert a job. Returns True if inserted, False if duplicate.
    job dict keys: title, company, location, url, source,
                   description, score, date_posted
    """
    h = make_hash(job.get("title", ""), job.get("company", ""), job.get("url", ""))
    if job_exists(h):
        return False

    conn = get_connection()
    conn.execute("""
        INSERT INTO jobs
            (job_hash, title, company, location, url, source,
             description, score, date_discovered, date_posted, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'new')
    """, (
        h,
        job.get("title", ""),
        job.get("company", ""),
        job.get("location", ""),
        job.get("url", ""),
        job.get("source", ""),
        job.get("description", ""),
        job.get("score", 0),
        datetime.now().isoformat(),
        job.get("date_posted", ""),
    ))
    conn.commit()
    conn.close()
    return True


def get_unnotified_jobs(limit: int = 20) -> list[dict]:
    """Fetch new jobs that haven't been notified yet."""
    conn = get_connection()
    rows = conn.execute("""
        SELECT * FROM jobs
        WHERE notified = 0 AND status = 'new'
        ORDER BY score DESC
        LIMIT ?
    """, (limit,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def mark_notified(job_ids: list[int]):
    conn = get_connection()
    conn.execute(
        f"UPDATE jobs SET notified = 1 WHERE id IN ({','.join('?' * len(job_ids))})",
        job_ids
    )
    conn.commit()
    conn.close()


def update_status(job_id: int, status: str, resume_path: str = None):
    """Update application status: new / applied / skipped."""
    conn = get_connection()
    if resume_path:
        conn.execute(
            "UPDATE jobs SET status = ?, resume_path = ? WHERE id = ?",
            (status, resume_path, job_id)
        )
    else:
        conn.execute("UPDATE jobs SET status = ? WHERE id = ?", (status, job_id))
    conn.commit()
    conn.close()


def log_run(jobs_found: int, jobs_new: int, jobs_notified: int):
    conn = get_connection()
    conn.execute("""
        INSERT INTO run_log (run_time, jobs_found, jobs_new, jobs_notified)
        VALUES (?, ?, ?, ?)
    """, (datetime.now().isoformat(), jobs_found, jobs_new, jobs_notified))
    conn.commit()
    conn.close()


def get_stats() -> dict:
    conn = get_connection()
    stats = {
        "total": conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0],
        "applied": conn.execute("SELECT COUNT(*) FROM jobs WHERE status='applied'").fetchone()[0],
        "new": conn.execute("SELECT COUNT(*) FROM jobs WHERE status='new'").fetchone()[0],
        "skipped": conn.execute("SELECT COUNT(*) FROM jobs WHERE status='skipped'").fetchone()[0],
    }
    conn.close()
    return stats


if __name__ == "__main__":
    init_db()
    print("[DB] Stats:", get_stats())
