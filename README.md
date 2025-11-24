# VeriCor Crawl + AI-First Dataset  
A fully automated system for crawling, cleaning, and exporting the VeriCor Medical Systems website into an **AI-ready dataset** — including Markdown content, JSON indexes, embeddings, and audit logs.

This repo is the single source of truth for the entire VeriCor Crawl pipeline.

---

# 🧭 Purpose

The VeriCor Crawl system automatically:

- Crawls the live **vericormed.com** website (pages, posts, products)
- Cleans + normalizes HTML into **Markdown**
- Generates:
  - `index_pages.json`
  - `index_posts.json`
  - `index_products.json`
  - `embeddings.jsonl`
- Maintains a structured AI-first dataset for:
  - SEO analysis  
  - Copywriting + content audits   
  - Internal VeriCor documentation  
  - Querying via the **VeriCor Agent** (custom GPT)
  - Future AI-integrated applications

The goal is to maintain an always-fresh *offline representation of the website* optimized for AI systems.

---

# ⚙️ Repository Structure

| Folder | Purpose |
|--------|---------|
| **ops/** | Automation scripts (Batch + PowerShell) for environment setup, refresh, and publishing. |
| **scripts/** | Python crawlers, cleaners, and exporters. |
| **data/** | Cached content, logs, and working files. |
| **exports/** | Final AI-ready outputs (indexes + embeddings). |
| **env/** | `.env` and environment bootstrap files. |
| **pages_clean/** | Cleaned Markdown output from crawlers. |

### Key Automation Files

| Script | Purpose |
|--------|---------|
| `ops/start_vericor_env.bat` | Activates the Python environment and loads `.env`. |
| `ops/refresh_audit.bat` | Runs **full crawl → clean → export → embed** pipeline. |
| `ops/publish_to_repo.ps1` | Smart Git publish script (prompts for message, stages modified files only). |
| `ops/publish_to_repo.bat` | Compatibility wrapper that calls the PowerShell publisher. |

---

# 🧑‍💻 Standard Operating Procedure (SOP)

This section is designed so anyone on the VeriCor team can run the system with minimal training.

---

## 1️⃣ Start the Environment

In **VS Code**, open the `vericor-crawl` folder.

Then run:

```bash
ops\start_vericor_env.bat
```

This:

- Activates the virtual environment  
- Loads API keys from `env/.env`  
- Confirms that Python, dependencies, and environment variables are properly configured  

---

## 2️⃣ Run a Full Website Refresh

In VS Code terminal:

```bash
ops\refresh_audit.bat
```

This performs:

1. Crawl pages/posts/products  
2. Clean + normalize to Markdown  
3. Rebuild JSON indexes  
4. Rebuild embeddings  
5. Produce a timestamped log in `data/logs/`

You're done when you see:

```
[DONE] Audit refresh complete
```

---

## 3️⃣ Publish the Updated Dataset to GitHub  
*(Optional but recommended after major changes.)*

Preferred method (PowerShell):

```bash
powershell -ExecutionPolicy Bypass -File ops\publish_to_repo.ps1
```

This script:

- Detects modified files  
- Prompts you for a commit message  
- Stages only changed files  
- Pushes to GitHub  

If you want it fully automated:

```bash
cmd /c "ops\publish_to_repo.bat commit message here"
```

---

## 4️⃣ Quick VS Code Publish  
Use the VS Code shortcut:

**Ctrl + Shift + B**

This runs the preconfigured task in `.vscode/tasks.json`:

- Calls the PowerShell publish script  
- Prompts for a commit message  

This is the fastest "Save → Publish" workflow.

---

# 🤖 VeriCor Agent (Custom GPT)

This repo is also connected to the **VeriCor Agent**, a custom GPT that:

- Reads your dataset through GitHub Actions  
- Can fetch or inspect Markdown, JSON, logs, and embeddings  
- Helps debug scripts or pipeline issues  
- Can run full audits through natural language commands  
- Can search the entire VeriCor dataset  

### Supported GPT Connector Actions

| Action | Description |
|--------|-------------|
| `getRepoFile` | Fetches any file from the repo (Markdown, JSON, Python, logs, etc.). |
| `listRepoTree` | Returns directory listings (with safeguards for large responses). |

The Agent now has **full read-level access** to the entire repository.

---

# 🛠 Notes & Known Issues

### ⚠️ Stray file: `from pathlib import Path.py`
This appears to be a mistaken or accidental file.  
Recommendation: **Delete it.**

### ⚠️ Old `ops/pages_clean` reference
You previously had a ZIP file called `pages_clean` in `ops/`.  
It has been removed; if it appears again, it should be deleted.

---

# 🧪 Testing the System

After each refresh, verify:

```bash
# Counts
powershell -Command "(Get-Content 'exports/embeddings.jsonl').Count"
powershell -Command "(Get-Content 'exports/index_pages.json' -Raw | ConvertFrom-Json).Count"
powershell -Command "(Get-Content 'exports/index_posts.json' -Raw | ConvertFrom-Json).Count"
powershell -Command "(Get-Content 'exports/index_products.json' -Raw | ConvertFrom-Json).Count"
```

Expected totals (typical):

- Pages: ~99  
- Posts: ~311  
- Products: ~224  
- Embedding chunks: ~3472  

---

# 📦 Monthly Automation (Optional)

A Windows Task Scheduler XML can be added to run:

- Environment initialization  
- Full refresh  
- Publish to GitHub  

This enables a fully automated monthly or weekly crawl.

---

# 📚 For Developers

### Adding new crawlers  
Place new Python modules under `scripts/`.

### Adding new automation  
Place batch/PowerShell scripts under `ops/`.

### Changing GitHub automation  
Modify:

- `.vscode/tasks.json`  
- `ops/publish_to_repo.ps1`

---

# ✔️ Next Steps (Recommended)

- Add Windows Task Scheduler automation for monthly refresh  
- Add more fine-grained GitHub API actions (write, update, delete)  
- Extend VeriCor Agent with:
  - "Search Markdown files"  
  - "Summarize a product page with SEO context"  
  - "Compare two versions of a page over time"  
