# 🤖 Automated Job Search Assistant
> Zero-cost · Fully local · Human-in-the-loop · Built for Chennai AI/ML freshers

---

## 📌 What This Does

Automatically discovers, filters, scores, and tailors resumes for fresher-friendly AI/ML jobs — then notifies you twice daily via **Telegram + Gmail**. You only do the final manual apply.

| Step | What happens | How |
|------|-------------|-----|
| 1 | Scrapes jobs | LinkedIn, Indeed, Glassdoor, Google Jobs, Naukri |
| 2 | Filters | Fresher/entry-level only, excludes senior roles |
| 3 | Scores | Skill match + title relevance + recency (0–100) |
| 4 | Tailors resume | Local LLM (Ollama) — no cloud, no cost |
| 5 | Notifies you | Telegram bot + Gmail at 12 PM & 8 PM IST |
| 6 | You apply | Manual only — avoids bans, maximises success |

---

## 🎯 Target Roles

- Graduate Trainee
- AI / ML Engineer
- Computer Vision Engineer
- Deep Learning Engineer
- Python Developer
- Automation Engineer
- Data Scientist

**Skills matched:** Python · Machine Learning · Deep Learning · Computer Vision · TensorFlow · PyTorch · OpenCV · Scikit-learn · Pandas · NumPy

---

## 📁 Project Structure
Automated Job Search System/
│
├── main.py                    # Entry point + scheduler
├── requirements.txt
│
├── config/
│   └── config.yaml            # All settings (credentials, roles, filters)
│
├── modules/
│   ├── init.py
│   ├── scraper.py             # Job discovery
│   ├── filter_score.py        # Fresher filter + scoring engine
│   ├── resume_tailor.py       # LLM-powered resume tailoring
│   ├── notifier.py            # Telegram + Email notifications
│   └── database.py            # SQLite job tracker
│
├── resumes/
│   ├── master_resume.md       # YOUR master resume (edit this)
│   └── output/                # Tailored resumes saved here
│
├── data/
│   └── jobs.db                # SQLite database (auto-created)
│
└── logs/
└── job_assistant.log

---

## ⚙️ Requirements

- Python 3.10+
- Windows / Linux / Mac
- [Ollama](https://ollama.ai) (local LLM)
- [Pandoc](https://pandoc.org/installing.html) (PDF/DOCX export)
- Telegram account
- Gmail account

---

## 🚀 Installation

### 1. Clone the repo

```bash
git clone https://github.com/yourusername/automated-job-search.git
cd "automated-job-search"
```

### 2. Create virtual environment

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# Mac/Linux
source .venv/bin/activate
```

### 3. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 4. Install Pandoc

- **Windows:** Download the `.msi` from [pandoc.org/installing.html](https://pandoc.org/installing.html) and install it. Then add to PATH:
```powershell
  [System.Environment]::SetEnvironmentVariable("PATH", $env:PATH + ";C:\Users\<YourName>\AppData\Local\Pandoc", "User")
```
- **Mac:** `brew install pandoc`
- **Linux:** `sudo apt install pandoc`

### 5. Install Ollama + pull model

```bash
# Install Ollama from https://ollama.ai
ollama pull llama3.1

# Start Ollama (keep running in background)
ollama serve
```

Lighter alternative (2 GB):
```bash
ollama pull qwen2.5
# Then set model: "qwen2.5" in config.yaml
```

---
## create logs and DB (if they are missing, setup them up, Adjust the directory based on your Device)
```
mkdir "D:\Automated Job Search System\logs"
mkdir "D:\Automated Job Search System\data"
mkdir "D:\Automated Job Search System\resumes\output"

```

## 🔧 Configuration

Edit `config/config.yaml`:

```yaml
candidate:
  name: "Your Full Name"

notifications:
  telegram:
    enabled: true
    bot_token: "YOUR_BOT_TOKEN"
    chat_id: "YOUR_CHAT_ID"
  email:
    enabled: true
    sender: "your@gmail.com"
    password: "YOUR_APP_PASSWORD"
    recipient: "your@gmail.com"
```

### Telegram Setup (2 min)

1. Open Telegram → search **@BotFather** → send `/newbot`
2. Follow prompts → copy the **bot token**
3. Search **@userinfobot** → send `/start` → copy your **chat ID**
4. Search your new bot → send `/start` to activate it

### Gmail App Password

1. Go to [myaccount.google.com/security](https://myaccount.google.com/security)
2. Enable **2-Step Verification**
3. Go to **App Passwords** → generate one for "Mail"
4. Copy the 16-character password into `config.yaml`

---

## ▶️ Usage

```powershell
# Check everything is set up correctly
python main.py --setup

# Send a test Telegram + Email notification
python main.py --test

# Run the full pipeline once (scrape → filter → tailor → notify)
python main.py --now

# Start the scheduler (runs at 12:00 PM & 8:00 PM IST daily)
python main.py

# Check your application stats
python main.py --status
```

### Run in background (Windows)

```powershell
Start-Process python -ArgumentList "main.py" -WindowStyle Hidden
```

### Run in background (Linux/Mac)

```bash
nohup python main.py > logs/run.log 2>&1 &
```

---

## 📊 How Scoring Works

Each job is scored out of 100:

| Factor | Weight | What it checks |
|--------|--------|---------------|
| Skill match | 50% | Python, ML, AI, CV, DL keywords in JD |
| Title match | 30% | How well title matches target roles |
| Recency | 20% | Jobs posted today score highest |

Only jobs scoring **40+** are kept. Top 15 per run are notified.

### Fresher Filter

**Included:** fresher · entry-level · junior · associate · 0–2 years · trainee · graduate

**Excluded:** senior · lead · manager · director · 5+ years · principal · architect

---

## 🤖 Resume Tailoring

For each top job, the LLM:
- Rewrites the summary to match the role
- Reorders skills to highlight matches
- Injects relevant keywords naturally
- Outputs: `.md` + `.pdf` + `.docx` in `resumes/output/`

**It never fabricates experience** — only reorders and adjusts emphasis.

---

## 🗄️ Tracking Applications

All jobs are stored in SQLite at `data/jobs.db`:
Status values: new → applied / skipped

Mark a job as applied:
```bash
sqlite3 data/jobs.db "UPDATE jobs SET status='applied' WHERE id=5;"
```

---

## 🛠️ Troubleshooting

| Error | Fix |
|-------|-----|
| `ModuleNotFoundError: modules` | Make sure `modules/__init__.py` exists and you run from the project root |
| `FileNotFoundError: logs/` | `mkdir logs data resumes\output` |
| `Ollama not running` | Run `ollama serve` in a separate terminal |
| `Pandoc not found` | Install from pandoc.org and add to PATH |
| `Gmail auth failed` | Use App Password, not your Gmail login password |
| `Telegram not working` | Send `/start` to your bot first, then test |
| `No jobs found` | Run during business hours (Mon–Fri 9am–6pm) |

---

## 📦 Dependencies
python-jobspy    # Multi-platform job scraping
requests         # HTTP calls
beautifulsoup4   # Naukri HTML parsing
schedule         # Twice-daily scheduler
pyyaml           # Config file parsing
pandas           # Data processing
markdown         # Markdown handling

External tools:
- [Ollama](https://ollama.ai) — local LLM engine
- [Pandoc](https://pandoc.org) — document conversion

---

## ⚠️ Important Notes

- **Never auto-applies** — manual application is intentional to avoid platform bans
- **Zero cloud cost** — Ollama runs 100% locally, no OpenAI/Anthropic API needed
- **No login scraping** — uses only public job listings
- Respect each platform's Terms of Service
- Add reasonable delays between requests (already built in)

---

## 🗺️ Roadmap

- [ ] Web dashboard for job tracking
- [ ] WhatsApp notifications
- [ ] Cover letter generation
- [ ] Interview preparation tips per job
- [ ] Company research automation

---

## 📄 License

MIT License — free to use, modify, and distribute.

---

*Built for Chennai AI/ML freshers. Zero cost. Zero cloud. Full control.* 🚀