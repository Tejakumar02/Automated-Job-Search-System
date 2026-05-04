"""
modules/notifier.py
Send job alerts via Telegram Bot AND Gmail SMTP.
Triggered twice daily: 12:00 PM IST and 8:00 PM IST.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


import smtplib
import yaml
import requests
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text      import MIMEText
from email.mime.base      import MIMEBase
from email                import encoders
from pathlib              import Path
from datetime             import datetime

log = logging.getLogger(__name__)


def load_config():
    with open("config/config.yaml") as f:
        return yaml.safe_load(f)


# ─── Format Job Message ───────────────────────────────────────────────────────

def format_job_card_telegram(job: dict, index: int) -> str:
    score_bar = "🟢" if job["score"] >= 70 else "🟡" if job["score"] >= 50 else "🔴"
    return (
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"*{index}. {job['title']}*\n"
        f"🏢 {job['company']}\n"
        f"📍 {job.get('location', 'India')}\n"
        f"🌐 Source: {job.get('source', '').upper()}\n"
        f"{score_bar} Match Score: *{job['score']}/100*\n"
        f"🔗 [Apply Here]({job.get('url', '#')})\n"
    )


def format_job_card_html(job: dict, index: int) -> str:
    score = job["score"]
    color = "#22c55e" if score >= 70 else "#f59e0b" if score >= 50 else "#ef4444"
    return f"""
    <tr>
      <td style="padding:12px; border-bottom:1px solid #e5e7eb;">
        <strong style="font-size:15px;">{index}. {job['title']}</strong><br>
        <span style="color:#6b7280;">🏢 {job['company']}</span> &nbsp;|&nbsp;
        <span style="color:#6b7280;">📍 {job.get('location','India')}</span><br>
        <span style="color:#6b7280;">Source: {job.get('source','').upper()}</span><br>
        <span style="background:{color};color:white;padding:2px 8px;border-radius:12px;font-size:12px;">
          ⭐ {score}/100 Match
        </span>
        &nbsp;&nbsp;
        <a href="{job.get('url','#')}" style="background:#2563eb;color:white;
           padding:4px 12px;border-radius:6px;text-decoration:none;font-size:12px;">
          Apply →
        </a>
      </td>
    </tr>"""


# ─── Telegram ─────────────────────────────────────────────────────────────────

def send_telegram(jobs: list[dict]) -> bool:
    cfg = load_config()
    tg  = cfg["notifications"]["telegram"]

    if not tg["enabled"]:
        return False

    bot_token = tg["bot_token"]
    chat_id   = tg["chat_id"]
    api_url   = f"https://api.telegram.org/bot{bot_token}/sendMessage"

    now   = datetime.now().strftime("%d %b %Y, %I:%M %p IST")
    count = len(jobs)

    # Header message
    header = (
        f"🤖 *Job Search Assistant*\n"
        f"📅 {now}\n"
        f"🎯 Found *{count} top-matched jobs* for you!\n\n"
        f"_Skills: Python | ML | AI | Computer Vision_\n"
    )

    try:
        # Send header
        requests.post(api_url, json={
            "chat_id": chat_id,
            "text": header,
            "parse_mode": "Markdown",
            "disable_web_page_preview": True,
        }, timeout=10)

        # Send job cards in batches (Telegram 4096 char limit)
        batch = ""
        for i, job in enumerate(jobs, 1):
            card = format_job_card_telegram(job, i)
            if len(batch) + len(card) > 3800:
                requests.post(api_url, json={
                    "chat_id":    chat_id,
                    "text":       batch,
                    "parse_mode": "Markdown",
                    "disable_web_page_preview": True,
                }, timeout=10)
                batch = ""
            batch += card + "\n"

        if batch:
            requests.post(api_url, json={
                "chat_id":    chat_id,
                "text":       batch,
                "parse_mode": "Markdown",
                "disable_web_page_preview": True,
            }, timeout=10)

        # Footer
        footer = (
            "✅ *Apply manually for best results.*\n"
            "📋 Tailored resumes are being generated...\n"
            "Use /status to check your application tracker."
        )
        requests.post(api_url, json={
            "chat_id":    chat_id,
            "text":       footer,
            "parse_mode": "Markdown",
        }, timeout=10)

        log.info(f"[Telegram] ✅ Sent {count} jobs")
        return True

    except Exception as e:
        log.error(f"[Telegram] ❌ Failed: {e}")
        return False


# ─── Email (Gmail SMTP) ───────────────────────────────────────────────────────

def send_email(jobs: list[dict]) -> bool:
    cfg   = load_config()
    email = cfg["notifications"]["email"]

    if not email["enabled"]:
        return False

    now   = datetime.now().strftime("%d %b %Y, %I:%M %p IST")
    count = len(jobs)

    job_rows = "".join(format_job_card_html(j, i) for i, j in enumerate(jobs, 1))

    html_body = f"""
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <style>
    body {{ font-family: 'Segoe UI', Arial, sans-serif; background:#f9fafb; margin:0; padding:0; }}
    .container {{ max-width:600px; margin:30px auto; background:white;
                  border-radius:12px; overflow:hidden;
                  box-shadow:0 4px 20px rgba(0,0,0,0.08); }}
    .header {{ background:linear-gradient(135deg,#1e40af,#7c3aed);
               color:white; padding:24px 32px; }}
    .header h1 {{ margin:0; font-size:22px; }}
    .header p  {{ margin:6px 0 0; opacity:0.85; font-size:13px; }}
    .body {{ padding:24px 32px; }}
    table {{ width:100%; border-collapse:collapse; }}
    .footer {{ background:#f1f5f9; padding:16px 32px;
               text-align:center; font-size:12px; color:#94a3b8; }}
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <h1>🤖 Job Search Assistant</h1>
      <p>📅 {now} &nbsp;|&nbsp; 🎯 {count} top-matched jobs found</p>
      <p>Skills: Python · ML · AI · Computer Vision · Data Science</p>
    </div>
    <div class="body">
      <p style="color:#374151; margin-top:0;">
        Here are today's best-matched fresher/entry-level opportunities:
      </p>
      <table>{job_rows}</table>
      <br>
      <p style="color:#6b7280; font-size:13px;">
        ✅ <strong>Apply manually</strong> for the best success rate.<br>
        📋 Tailored resumes are automatically generated in <code>resumes/output/</code>
      </p>
    </div>
    <div class="footer">
      Job Search Assistant · Fully local · Zero cost · Built with ❤️ in Chennai
    </div>
  </div>
</body>
</html>
"""

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"🎯 {count} New Job Matches — {now}"
    msg["From"]    = email["sender"]
    msg["To"]      = email["recipient"]
    msg.attach(MIMEText(html_body, "html"))

    try:
        with smtplib.SMTP(email["smtp_host"], email["smtp_port"]) as smtp:
            smtp.ehlo()
            smtp.starttls()
            smtp.login(email["sender"], email["password"])
            smtp.sendmail(email["sender"], email["recipient"], msg.as_string())

        log.info(f"[Email] ✅ Sent {count} jobs to {email['recipient']}")
        return True

    except Exception as e:
        log.error(f"[Email] ❌ Failed: {e}")
        return False


# ─── Combined Notifier ────────────────────────────────────────────────────────

def notify_all(jobs: list[dict]) -> dict:
    """
    Send notifications via all enabled channels.
    Returns dict with success status per channel.
    """
    if not jobs:
        log.info("[Notifier] No new jobs to notify.")
        return {"telegram": False, "email": False}

    results = {
        "telegram": send_telegram(jobs),
        "email":    send_email(jobs),
    }
    log.info(f"[Notifier] Results: {results}")
    return results


def send_test_notification():
    """Quick test to verify credentials are working."""
    test_jobs = [
        {
            "title":    "Junior ML Engineer",
            "company":  "TestCorp India",
            "location": "Chennai, TN",
            "source":   "linkedin",
            "score":    85.0,
            "url":      "https://linkedin.com/jobs/test",
        },
        {
            "title":    "Python Developer - Fresher",
            "company":  "StartupAI",
            "location": "Remote / Chennai",
            "source":   "naukri",
            "score":    72.5,
            "url":      "https://naukri.com/jobs/test",
        },
    ]
    log.info("[Notifier] Sending test notification...")
    return notify_all(test_jobs)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    send_test_notification()
