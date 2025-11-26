# VeriCor Crawl & AI Dataset – Human Operations Manual

This manual explains how to use the **VeriCor Crawl + AI-first dataset** in plain language. You do *not* need to be a programmer to run it successfully.

The system’s job is to:

1. Crawl **vericormed.com**
2. Convert everything to clean, structured Markdown
3. Build AI-ready indexes + embeddings
4. Save the results and (optionally) publish them to GitHub so the **VeriCor Agent GPT** can use them

Once you complete a refresh and publish, the VeriCor Agent GPT can answer deep, accurate questions based on the latest site snapshot.

---

## 1. Who This Is For

This manual is for:

- **Doug**, who built and maintains the system.
- **VeriCor team members** who may need to:
  - Refresh the dataset
  - Confirm everything ran correctly
  - Publish updates so the GPT can use them

You only need to be comfortable with:

- Opening folders
- Double-clicking a `.bat` file
- Pressing a keyboard shortcut in VS Code

---

## 2. What the System Does (Plain English)

Every time you run a **full refresh**, the system:

1. **Crawls the live site**  
   Visits pages, posts, and products on `https://www.vericormed.com`.

2. **Cleans and organizes content**  
   Stores clean Markdown files under:
   - `data/pages_clean/pages/`
   - `data/pages_clean/posts/`
   - `data/pages_clean/products/`

3. **Builds small “index” files**  
   These summarize each page/post/product for quick lookup:
   - `exports/index_pages.json`
   - `exports/index_posts.json`
   - `exports/index_products.json`

4. **Builds embeddings**  
   These are numeric representations for AI search:
   - `exports/embeddings.jsonl`

5. **Logs everything**  
   Each run writes a log file like:
   - `data/logs/refresh_YYYYMMDD_HHMMSS.log`

6. **Supports publishing to GitHub**  
   So the **VeriCor Agent GPT** and collaborators can use the latest dataset.

In one sentence:

> Crawl website → clean → index → embed → log → (optionally) publish.

---

## 3. Folder Overview (Important Locations)

On Doug’s computer, the project lives at:

    C:\Users\Finn\Projects\vericor-crawl

Key folders and what they mean:

- `ops/`  
  Automation scripts:
  - `start_vericor_env.bat`
  - `refresh_audit.bat`
  - `publish_to_repo.ps1` (used by VS Code task)

- `scripts/`  
  Python code that does the crawling and exporting (developer-only).

- `data/`  
  Working data:
  - `data/pages_clean/` → clean Markdown
  - `data/logs/` → refresh logs

- `exports/`  
  AI-ready outputs:
  - `index_pages.json`
  - `index_posts.json`
  - `index_products.json`
  - `embeddings.jsonl`

- `docs/`  
  Documentation:
  - `human-operations-manual.md` (this file)
  - `gpt-system-manual.md` (for the VeriCor Agent)

- `.vscode/`  
  VS Code configuration including the “Publish to GitHub” task.

You will primarily interact with:

- `ops/start_vericor_env.bat`
- `ops/refresh_audit.bat`
- VS Code shortcut: `Ctrl + Shift + B` (publish)

---

## 4. Quick Start (Minimal Steps)

When you just want to refresh and publish with minimal thinking, do this:

1. **Start the environment**
   - Open: `C:\Users\Finn\Projects\vericor-crawl`
   - Double-click: `ops\start_vericor_env.bat`
   - Wait until you see a prompt like:  
     `C:\Users\Finn\Projects\vericor-crawl\ops>`

2. **Run the full refresh**
   - In that window, type:  
     `refresh_audit.bat`  
     and press Enter.
   - Wait for the `[DONE]` message.

3. **Publish to GitHub**
   - Open VS Code with the `vericor-crawl` folder.
   - Press: `Ctrl + Shift + B`
   - When asked for a commit message, enter something like:  
     `chore: full dataset refresh 2025-11-26`
   - Press Enter.

After that, the **VeriCor Agent GPT** has access to the current dataset.

---

## 5. Detailed Workflow

### 5.1 Start the VeriCor Crawl Environment

Always do this first so the correct Python environment and variables are loaded.

Steps:

1. Open File Explorer and go to:

       C:\Users\Finn\Projects\vericor-crawl

2. Double-click:

       ops\start_vericor_env.bat

3. You should see a window with something like:

       [INFO] Project root: C:\Users\Finn\Projects\vericor-crawl
       [INFO] Loaded environment vars from C:\Users\Finn\Projects\vericor-crawl\env\.env

       [ENVIRONMENT READY]
       Python version:
       Python 3.13.5

       You are now in the VeriCor Crawl environment.
       Type <python scriptname.py> or run ops\refresh_audit.bat

       C:\Users\Finn\Projects\vericor-crawl\ops>

If the window opens and stays open with an `ops>` prompt, you’re good.

---

### 5.2 Run the Full Refresh

In that same environment window, run:

    refresh_audit.bat

What happens behind the scenes:

- The script determines a log file name (stored in `data/logs/`).
- It runs the Python pipeline that:
  - Crawls the live site
  - Cleans HTML to Markdown
  - Organizes pages/posts/products
  - Exports indexes
  - Builds embeddings
- It then prints the tail (last lines) of the log.

You’ll see progress, including an “Embedding” progress bar and finally something like:

    [ok] Wrote C:\Users\Finn\Projects\vericor-crawl\exports\embeddings.jsonl  (docs: 634, chunks: 3472)
    [DONE] Audit refresh complete. Log: C:\Users\Finn\Projects\vericor-crawl\data\logs\refresh_YYYYMMDD_HHMMSS.log

If you see the `[DONE]` line, the run finished successfully.

---

### 5.3 Optional: Sanity Check the Outputs

If you want to confirm that everything looks healthy:

1. Open VS Code with the `vericor-crawl` folder.
2. Open the integrated terminal (View → Terminal).
3. Run the following checks (PowerShell syntax):

    powershell -NoProfile -Command "(Get-Content 'exports\index_pages.json'    -Raw | ConvertFrom-Json).Count"
    powershell -NoProfile -Command "(Get-Content 'exports\index_posts.json'    -Raw | ConvertFrom-Json).Count"
    powershell -NoProfile -Command "(Get-Content 'exports\index_products.json' -Raw | ConvertFrom-Json).Count"
    powershell -NoProfile -Command "(Get-Content 'exports\embeddings.jsonl').Count"

You don’t need exact numbers memorized, but they should be non-zero and consistent with past runs.

If any of these return 0 or throw errors, see the Troubleshooting section.

---

### 5.4 Publish to GitHub (So the GPT Can Use It)

Publishing your changes makes the refreshed dataset visible to the **VeriCor Agent GPT** via the GitHub connector.

Standard workflow:

1. Open VS Code in the `vericor-crawl` folder.
2. Press:

       Ctrl + Shift + B

3. A prompt will appear in the terminal asking for a commit message.  
   Use a clear message such as:

       chore: dataset refresh 2025-11-26

4. Press Enter.

The publish script (`ops/publish_to_repo.ps1`) will:

- Check for changes
- Stage them
- Commit with your message
- Push the commit to the GitHub repo:  
  `https://github.com/VeriCorMed/vericor-ai-first-crawl`

If everything works, you’ll see confirmation that the changes were pushed.

Once this is done, the VeriCor Agent GPT has access to the latest dataset.

---

## 6. When to Run a Refresh

Good times to run the full pipeline:

- After significant website content updates:
  - New products
  - Major copy revisions
  - New landing pages or blog posts

- Before planning or strategy sessions:
  - You want the GPT to analyze the most current content.

- Before large campaigns:
  - To ensure product and messaging details are current.

- On a regular schedule:
  - For example, once per month, or before major reviews.

If nothing important has changed on the website, you do not need to refresh.

---

## 7. How VeriCor Agent GPT Uses This

Once a refresh is complete and pushed:

- The VeriCor Agent GPT uses its GitHub connector to:
  - Read `README.md` and `docs/*.md` for instructions
  - Read indexes in `exports/`
  - Understand folder layout and script behavior

This allows you to ask questions like:

- “How many products are in the dataset?”
- “Explain what `refresh_audit.bat` does.”
- “Show me all pages related to alternate care sites.”
- “Help me find outdated product copy.”

The agent is not guessing; it is reading directly from your repository.

---

## 8. Troubleshooting

### 8.1 `start_vericor_env.bat` window flashes and closes

If you double-click the file and the window closes immediately:

1. Open a manual command prompt:
   - Press Win + R
   - Type `cmd` and press Enter

2. In the command prompt, run:

       cd C:\Users\Finn\Projects\vericor-crawl
       ops\start_vericor_env.bat

3. If there is an error, it will stay visible.  
   Copy the text or take a screenshot for Doug or support.

---

### 8.2 Error: `. was unexpected at this time.`

This can happen if a batch script is malformed or partially edited.  
Current versions of the scripts have been fixed, so this should be rare.

If it reappears:

- Make sure you’re using the latest committed scripts from GitHub.
- Avoid editing `.bat` files unless you’re deliberately working on them with Doug.
- If it persists, capture the console output and share it.

---

### 8.3 Publish task says “Nothing to commit”

This means:

- There are no changes Git cares about; or
- Newly created files (like new docs) haven’t been staged yet.

Normal scenario:

- After a refresh, there *should* be changes in `exports/`.
- If `Ctrl + Shift + B` says “Nothing to commit” but you expected changes, Doug may need to:
  - Confirm that the files actually changed.
  - Run `git status` and `git add` manually for new folders (like `/docs`) the first time.

---

### 8.4 The GPT seems out of date

If VeriCor Agent GPT seems unaware of recent content:

- Make sure you:
  1. Ran `refresh_audit.bat`
  2. Published via `Ctrl + Shift + B`
- Confirm on GitHub that your most recent commit is visible.
- Then ask the GPT something like:
  - “Confirm you are using the latest indexes from `exports/index_products.json`.”

If it still seems off, Doug can investigate whether the connector is pointing at the correct repo/branch.

---

## 9. Things You Should Not Touch

For non-developers, the following are **read-only**:

- `env/.env`  
  Contains API keys and secret configuration  
  (never share or commit this file).

- `scripts/*.py`  
  All Python logic for crawling, cleaning, and exporting.

- `ops/start_vericor_env.bat`  
- `ops/refresh_audit.bat`  
- `ops/publish_to_repo.ps1`  

These are automation scripts that have been tuned and tested.  
You should run them, but not edit them.

If you think one of these needs to change, coordinate with Doug.

---

## 10. Glossary

- **Crawl**  
  Automated process of visiting pages on the website and downloading their content.

- **Markdown (`.md`)**  
  Simple text format that supports headings, lists, links, and basic formatting.

- **Index files (`.json`)**  
  Lightweight, structured summaries of content. Used for fast lookups and analysis.

- **Embeddings (`embeddings.jsonl`)**  
  Numeric vectors representing text meaning; used for AI search and similarity.

- **Repository / Repo**  
  The GitHub project:  
  `https://github.com/VeriCorMed/vericor-ai-first-crawl`

- **Commit**  
  A saved checkpoint of changes in Git.

- **Publish / Push**  
  Sending local commits up to GitHub.

- **Dataset**  
  The combination of Markdown, index files, and embeddings that the GPT uses.

---

## 11. Final Summary

When you need to update the AI-ready dataset:

1. Run `ops/start_vericor_env.bat`
2. Run `refresh_audit.bat`
3. In VS Code, press `Ctrl + Shift + B` and add a clear commit message

That’s the complete “human” workflow.  
Everything else (Python details, embeddings math, etc.) can be left to Doug and the VeriCor Agent GPT.

If anything looks or feels off, save the error message or screenshot and pass it along. The whole system is designed to be understandable, inspectable, and fixable over time.
