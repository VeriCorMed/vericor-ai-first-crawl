# VeriCor Crawl + AI-First Dataset  
A living system for creating, refreshing, and maintaining an AI-ready dataset of the VeriCor Medical Systems website.

---

## 🧭 Purpose
This toolkit automatically:
- Crawls the live [vericormed.com](https://www.vericormed.com) website.
- Cleans and normalizes pages, posts, and products into Markdown.
- Builds AI-optimized JSON indexes and embeddings.
- Exports all cleaned data for analysis, SEO audits, and AI querying.

The goal: keep an always-current “AI-first” snapshot of VeriCor’s website that can be queried, audited, or analyzed by AI systems.

---

## ⚙️ System Overview

| Folder | Purpose |
|---------|----------|
| **ops/** | Batch files that run and automate the pipeline. |
| **scripts/** | Python scripts for crawling, cleaning, and exporting. |
| **data/** | Cleaned Markdown content and log files. |
| **exports/** | Final AI-ready JSON indexes and embeddings. |
| **env/** | Environment settings, including the `.env` file with secure API keys. |

Key scripts:
- `ops/start_vericor_env.bat` → Activates the Python environment.
- `ops/refresh_audit.bat` → Runs the full crawl/index/embedding refresh.
- `ops/publish_to_repo.bat` → Pushes updates to GitHub (optional).

---

## 🧑‍💻 Standard Operating Procedure (SOP)

### 1️⃣ Start the Environment
Open **Visual Studio Code** and the `vericor-crawl` folder.

In the integrated terminal:
```bash
ops\start_vericor_env.bat

