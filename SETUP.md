# 🤖 Job Search Assistant — Setup Guide
## Zero-Cost | Fully Local | Chennai, India

---

## ⚡ Quick Start (5 Steps)

### Step 1 — Install Python Dependencies
```bash
cd job_assistant
pip install -r requirements.txt
```

### Step 2 — Install System Tools
```bash
# Pandoc (for PDF/DOCX resume export)
sudo apt install pandoc texlive-latex-base

# Ollama (local LLM for resume tailoring)
curl -fsSL https://ollama.ai/install.sh | sh

# Pull the LLM model (one-time, ~4GB)
ollama pull llama3.1
# OR lighter alternative:
ollama pull qwen2.5
```

### Step 3 — Configure Your Settings
Edit `config/config.yaml`:

```yaml
# Fill in YOUR details:
candidate:
  name: "Your Full Name"

notifications:
  telegram:
    bot_token: "YOUR_BOT_TOKEN"    # Step 3a below
    chat_id: "YOUR_CHAT_ID"        # Step 3b below
  email:
    sender: "your@gmail.com"
    password: "YOUR_APP_PASSWORD"  # Step 3c below
    recipient: "your@gmail.com"
```

#### Step 3a — Create Telegram Bot
1. Open Telegram → search **@BotFather**
2. Send: `/newbot`
3. Follow prompts, copy the **bot token**
4. Paste into `config.yaml → telegram → bot_token`

#### Step 3b — Get Your Chat ID
1. Open Telegram → search **@userinfobot**
2. Send: `/start`
3. Copy the **id** number
4. Paste into `config.yaml → telegram → chat_id`

#### Step 3c — Gmail App Password
1. Go to **myaccount.google.com/security**
2. Enable **2-Step Verification**
3. Go to **App Passwords** → Select app: Mail → Generate
4. Copy the 16-character password
5. Paste into `config.yaml → email → password`

### Step 4 — Edit Your Resume
Edit `resumes/master_resume.md` with your actual details:
- Replace "Your Full Name" with your name
- Add your real projects, education, skills
- Keep it in Markdown format

### Step 5 — Run Setup Check
```bash
python main.py --setup
```
All green? You're ready! 🎉

---

## 🚀 Running the System

```bash
# Run once immediately (test the full pipeline)
python main.py --now

# Start the scheduler (runs at 12:00 PM & 8:00 PM IST daily)
python main.py

# Send a test notification (verify Telegram + Email)
python main.py --test

# Check job tracker stats
python main.py --status
```

---

## 📁 Project Structure

```
job_assistant/
├── main.py                    # 🚀 Entry point + scheduler
├── config/
│   └── config.yaml            # ⚙️  All settings here
├── modules/
│   ├── scraper.py             # 📡 Job discovery (LinkedIn, Indeed, etc.)
│   ├── filter_score.py        # 🔍 Fresher filter + scoring engine
│   ├── resume_tailor.py       # 🤖 LLM-powered resume tailoring
│   ├── notifier.py            # 📬 Telegram + Email notifications
│   └── database.py            # 💾 SQLite tracker
├── resumes/
│   ├── master_resume.md       # 📋 YOUR master resume (edit this)
│   └── output/                # 📂 Tailored resumes saved here
├── data/
│   └── jobs.db                # 🗄️  SQLite database (auto-created)
├── logs/
│   └── job_assistant.log      # 📝 Logs
└── requirements.txt
```

---

## 🔄 Daily Workflow (What Happens Automatically)

```
12:00 PM IST & 8:00 PM IST:
  ┌─────────────────────────────────────────────┐
  │  1. Scrape LinkedIn, Indeed, Glassdoor,     │
  │     Google Jobs, Naukri                     │
  │  2. Filter: fresher/entry-level only        │
  │  3. Score: skill match + title + recency    │
  │  4. Save top 15 to SQLite (no duplicates)   │
  │  5. Tailor resume with Ollama LLM           │
  │  6. Send Telegram + Email notification      │
  └─────────────────────────────────────────────┘

YOU receive notification with:
  → Job title, company, score, apply link
  → Tailored resume ready in resumes/output/
  → Manually review and apply 🎯
```

---

## 🛠️ Troubleshooting

| Problem | Fix |
|---------|-----|
| `Ollama not running` | Run `ollama serve` in a separate terminal |
| `No jobs found` | Try `python main.py --now` during business hours |
| `Telegram not working` | Verify bot token and chat ID; message the bot first |
| `Email fails` | Use App Password (not your Gmail login password) |
| `PDF export fails` | `sudo apt install pandoc texlive-latex-base` |
| `ImportError: jobspy` | `pip install python-jobspy` |

---

## 🔧 Customisation Tips

**Change target roles** → Edit `config.yaml → target_roles`  
**Adjust score threshold** → Edit `config.yaml → filtering → min_score`  
**Change schedule times** → Edit `config.yaml → job_search → schedule_times`  
**Switch LLM model** → Edit `config.yaml → ollama → model` (must be pulled)  
**Add more skills** → Edit `config.yaml → candidate → skills`  

---

## 📊 Tracking Your Applications

```bash
python main.py --status
```

To manually mark a job as applied, open the SQLite DB:
```bash
sqlite3 data/jobs.db
UPDATE jobs SET status='applied' WHERE id=5;
.quit
```

---

*Built for Chennai AI/ML freshers. Zero cost. Zero cloud. Full control.* 🚀









C:\Users\tejak\AppData\Local\Pandoc