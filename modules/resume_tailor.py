"""
modules/resume_tailor.py
Tailor the master resume for each job using a local Ollama LLM.
Outputs ATS-friendly Markdown, PDF, and DOCX — zero cloud cost.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


import re
import json
import yaml
import requests
import subprocess
from pathlib import Path
from datetime import datetime
import logging

log = logging.getLogger(__name__)


def load_config():
    with open("config/config.yaml") as f:
        return yaml.safe_load(f)


# ─── Ollama LLM Call ──────────────────────────────────────────────────────────

def ollama_generate(prompt: str, system: str = "") -> str:
    """
    Call local Ollama API. Model must be pulled: ollama pull llama3.1
    """
    cfg = load_config()
    url = f"{cfg['ollama']['base_url']}/api/generate"

    payload = {
        "model":  cfg["ollama"]["model"],
        "prompt": prompt,
        "system": system,
        "stream": False,
        "options": {"temperature": 0.3, "num_predict": 2000},
    }

    try:
        resp = requests.post(url, json=payload, timeout=cfg["ollama"]["timeout"])
        resp.raise_for_status()
        return resp.json().get("response", "").strip()
    except requests.exceptions.ConnectionError:
        log.error("❌ Ollama not running. Start with: ollama serve")
        return ""
    except Exception as e:
        log.error(f"Ollama error: {e}")
        return ""


# ─── JD Key Requirement Extractor ────────────────────────────────────────────

def extract_jd_requirements(jd_text: str) -> dict:
    """
    Use LLM to extract structured requirements from job description.
    Returns dict with: skills, role_summary, experience, keywords
    """
    prompt = f"""
Extract key requirements from this job description.
Return ONLY valid JSON with these keys:
- "role_summary": one sentence what this role does
- "required_skills": list of technical skills mentioned
- "preferred_skills": list of nice-to-have skills
- "experience": experience requirement string
- "keywords": list of important ATS keywords

Job Description:
{jd_text[:3000]}

Return only the JSON object, no explanation.
"""
    response = ollama_generate(prompt)

    # Clean and parse JSON
    try:
        # Strip markdown code fences if present
        clean = re.sub(r"```json|```", "", response).strip()
        return json.loads(clean)
    except Exception:
        log.warning("Could not parse JD extraction JSON, using fallback")
        return {
            "role_summary": "",
            "required_skills": [],
            "preferred_skills": [],
            "experience": "",
            "keywords": [],
        }


# ─── Resume Tailoring ─────────────────────────────────────────────────────────

def tailor_resume(master_resume: str, job: dict) -> str:
    """
    Use local LLM to tailor the master resume for a specific job.
    Does NOT fabricate experience — only reorders and adjusts emphasis.
    """
    jd_reqs = extract_jd_requirements(job.get("description", ""))

    system_prompt = """You are an expert ATS resume writer. Your task is to tailor
a resume for a specific job posting. CRITICAL RULES:
1. NEVER invent or fabricate any experience, skills, or achievements
2. Only reorder bullet points, adjust emphasis, and add relevant keywords naturally
3. Keep all content factually accurate to the original resume
4. Make the summary specific to this role
5. Output clean ATS-friendly Markdown only — no HTML, no tables
6. Inject keywords naturally into existing descriptions where they genuinely fit
7. Do NOT keyword-stuff"""

    prompt = f"""
Tailor this resume for the job below.

JOB TITLE: {job.get('title', '')}
COMPANY: {job.get('company', '')}
ROLE SUMMARY: {jd_reqs.get('role_summary', '')}
REQUIRED SKILLS: {', '.join(jd_reqs.get('required_skills', []))}
KEY KEYWORDS: {', '.join(jd_reqs.get('keywords', []))}

MASTER RESUME:
{master_resume}

OUTPUT: Return the complete tailored resume in Markdown format.
- Rewrite the Professional Summary to specifically target this role
- Reorder skills to put matching ones first
- Subtly adjust bullet points to emphasize relevant experience
- Do NOT add anything that wasn't in the original resume
"""

    tailored = ollama_generate(prompt, system=system_prompt)

    if not tailored:
        log.warning("LLM returned empty response — using master resume as fallback")
        return master_resume

    return tailored


# ─── Export Functions ─────────────────────────────────────────────────────────

def export_to_pdf(md_content: str, output_path: str) -> bool:
    """
    Convert Markdown → PDF using pandoc (free, local).
    Install: sudo apt install pandoc texlive-latex-base
    """
    md_tmp = output_path.replace(".pdf", "_tmp.md")
    Path(md_tmp).write_text(md_content, encoding="utf-8")

    cmd = [
        "pandoc", md_tmp,
        "-o", output_path,
        "--pdf-engine=pdflatex",
        "-V", "geometry:margin=1in",
        "-V", "fontsize=11pt",
        "--highlight-style=tango",
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        Path(md_tmp).unlink(missing_ok=True)
        if result.returncode == 0:
            log.info(f"📄 PDF exported: {output_path}")
            return True
        else:
            log.error(f"PDF export failed: {result.stderr}")
            return False
    except FileNotFoundError:
        log.warning("pandoc not found. Install: sudo apt install pandoc")
        return False


def export_to_docx(md_content: str, output_path: str) -> bool:
    """
    Convert Markdown → DOCX using pandoc.
    """
    md_tmp = output_path.replace(".docx", "_tmp.md")
    Path(md_tmp).write_text(md_content, encoding="utf-8")

    cmd = ["pandoc", md_tmp, "-o", output_path]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        Path(md_tmp).unlink(missing_ok=True)
        if result.returncode == 0:
            log.info(f"📝 DOCX exported: {output_path}")
            return True
        else:
            log.error(f"DOCX export failed: {result.stderr}")
            return False
    except FileNotFoundError:
        log.warning("pandoc not found. Install: sudo apt install pandoc")
        return False


# ─── Main Entry ───────────────────────────────────────────────────────────────

def process_job_resume(job: dict) -> dict:
    """
    Full pipeline: load master → tailor → export PDF + DOCX.
    Returns paths to generated files.
    """
    cfg = load_config()
    master_path = Path(cfg["resumes"]["master_resume"])
    output_dir  = Path(cfg["resumes"]["output_dir"])
    output_dir.mkdir(parents=True, exist_ok=True)

    if not master_path.exists():
        log.error(f"Master resume not found: {master_path}")
        return {}

    master_resume = master_path.read_text(encoding="utf-8")

    # Generate safe filename
    safe_title   = re.sub(r"[^\w\s-]", "", job.get("title", "job")).replace(" ", "_")
    safe_company = re.sub(r"[^\w\s-]", "", job.get("company", "co")).replace(" ", "_")
    timestamp    = datetime.now().strftime("%Y%m%d_%H%M")
    base_name    = f"{safe_title}_{safe_company}_{timestamp}"

    md_path   = str(output_dir / f"{base_name}.md")
    pdf_path  = str(output_dir / f"{base_name}.pdf")
    docx_path = str(output_dir / f"{base_name}.docx")

    log.info(f"🤖 Tailoring resume for: {job.get('title')} @ {job.get('company')}")
    tailored_md = tailor_resume(master_resume, job)

    # Save Markdown
    Path(md_path).write_text(tailored_md, encoding="utf-8")
    log.info(f"📋 Markdown saved: {md_path}")

    # Export formats
    export_to_pdf(tailored_md, pdf_path)
    export_to_docx(tailored_md, docx_path)

    return {
        "markdown": md_path,
        "pdf":      pdf_path,
        "docx":     docx_path,
    }


if __name__ == "__main__":
    # Test with a dummy job
    test_job = {
        "title":       "Junior ML Engineer",
        "company":     "TestCorp",
        "description": "Looking for a Python developer with ML skills. Must know scikit-learn, pandas. Fresher welcome.",
    }
    paths = process_job_resume(test_job)
    print("Generated files:", paths)
