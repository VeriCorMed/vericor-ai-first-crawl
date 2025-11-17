@echo off
setlocal ENABLEDELAYEDEXPANSION

REM ╔══════════════════════════════════════════════════════════════════╗
REM ║ VeriCor Crawl + Audit Refresh                                    ║
REM ╚══════════════════════════════════════════════════════════════════╝

REM -- Locate repo root (this file lives in ...\vericor-crawl\ops)
set "SCRIPT_DIR=%~dp0"
pushd "%SCRIPT_DIR%\.."
set "ROOT=%CD%"

REM -- Choose Python: prefer venv, else system
set "PY=%ROOT%\venv\Scripts\python.exe"
if not exist "%PY%" set "PY=python"

REM -- Logs
set "LOGDIR=%ROOT%\data\logs"
if not exist "%LOGDIR%" mkdir "%LOGDIR%" >nul 2>&1
for /f "tokens=1-3 delims=/ " %%a in ("%date%") do (set "Y=%%c" & set "M=%%a" & set "D=%%b")
for /f "tokens=1-3 delims=:." %%h in ("%time%") do (set "HH=%%h" & set "MM=%%i" & set "SS=%%j")
set "HH=%HH: =0%"
set "STAMP=%Y%%M%%D%_%HH%%MM%"
set "LOG=%LOGDIR%\refresh_%STAMP%.log"

echo ====================================================== 
echo  VeriCor Crawl + Audit
echo  Root: %ROOT%
echo  Log:  %LOG%
echo ====================================================== 
echo. 

REM --------------------- RUN STEPS ----------------------

REM 1) (Optional) Crawl site → Markdown
REM %PY% scripts\crawl\deep_crawl_vcm.py >> "%LOG%" 2>&1

REM 2) (Optional) Clean/normalize markdown (pages/posts/products)
REM %PY% scripts\processing\preprocess_clean.py >> "%LOG%" 2>&1
REM %PY% scripts\processing\clean_vc_shortcodes.py >> "%LOG%" 2>&1
REM %PY% scripts\processing\normalize_pages_format.py >> "%LOG%" 2>&1
REM %PY% scripts\processing\normalize_product_frontmatter.py >> "%LOG%" 2>&1
REM %PY% scripts\processing\inject_page_videos.py >> "%LOG%" 2>&1
REM %PY% scripts\processing\add_inline_videos.py >> "%LOG%" 2>&1

REM 3) (Optional) WooCommerce export → products md
REM %PY% scripts\export\export_products.py >> "%LOG%" 2>&1

REM 4) Always rebuild indexes
%PY% scripts\export\build_indexes.py >> "%LOG%" 2>&1

REM 5) Rebuild embeddings (MiniLM default)
%PY% scripts\export\build_embeddings.py --model all-MiniLM-L6-v2 >> "%LOG%" 2>&1

REM 6) Move the large links.jsonl out of tracked exports (if present)
if exist "%ROOT%\exports\links.jsonl" (
  if not exist "%ROOT%\exports\_private" mkdir "%ROOT%\exports\_private" >nul 2>&1
  move /Y "%ROOT%\exports\links.jsonl" "%ROOT%\exports\_private\links.jsonl" >nul
  echo [INFO] Moved large links.jsonl to exports\_private >> "%LOG%"
)

echo. 
echo [DONE] Audit refresh complete. Log: %LOG%

REM -- show last ~80 lines
powershell -NoProfile -Command "$p='%LOG%'; Write-Host '--- LOG TAIL ---'; if (Test-Path $p) { Get-Content $p -Tail 80 } else { Write-Host 'Log not found.' }"
echo.
pause
popd
endlocal
