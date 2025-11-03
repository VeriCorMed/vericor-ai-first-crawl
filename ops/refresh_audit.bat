@echo off
REM ======================================================
REM  refresh_audit.bat — VeriCor Crawl + Audit (robust, no big () blocks)
REM  - Locale-proof timestamped logs
REM  - Works from double-click in ops\ or from project root
REM  - Venv + .env loading
REM  - Full refresh OR incremental (updated_pages/posts.txt)
REM  - AI-first indexes + embeddings
REM ======================================================

SETLOCAL ENABLEEXTENSIONS ENABLEDELAYEDEXPANSION

REM ---- Resolve project root (parent of /ops)
SET "SCRIPT_DIR=%~dp0"
PUSHD "%SCRIPT_DIR%\.."
SET "ROOT=%CD%"

REM ---- Logs dir + timestamped logfile (locale-proof)
IF NOT EXIST "%ROOT%\data\logs" MKDIR "%ROOT%\data\logs"
FOR /F %%t IN ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd_HHmmss"') DO SET "TS=%%t"
SET "LOGFILE=%ROOT%\data\logs\refresh_%TS%.log"

REM ---- Header
echo(
echo ======================================================
echo  VeriCor Crawl + Audit
echo  Root: %ROOT%
echo  Log:  %LOGFILE%
echo ======================================================
echo(

REM ---- Activate venv (support both locations)
IF EXIST "%ROOT%\venv\Scripts\activate.bat" (
  CALL "%ROOT%\venv\Scripts\activate.bat" >> "%LOGFILE%" 2>&1
) ELSE IF EXIST "%ROOT%\env\venv\Scripts\activate.bat" (
  CALL "%ROOT%\env\venv\Scripts\activate.bat" >> "%LOGFILE%" 2>&1
) ELSE (
  echo [ERROR] No virtual environment found at %ROOT%\venv or %ROOT%\env\venv
  echo Create one with: python -m venv venv
  GOTO :END_FAIL
)

REM ---- Load .env (root or env\.env)
SET "ENV_FILE="
IF EXIST "%ROOT%\.env"     SET "ENV_FILE=%ROOT%\.env"
IF EXIST "%ROOT%\env\.env" SET "ENV_FILE=%ROOT%\env\.env"
IF DEFINED ENV_FILE (
  FOR /F "usebackq tokens=1* delims== eol=#" %%A IN ("%ENV_FILE%") DO (
    IF NOT "%%~A"=="" SET "%%A=%%B"
  )
)

REM ---- Stable Python I/O
SET "PYTHONUTF8=1"
SET "PYTHONIOENCODING=utf-8"

REM ---- Log basic env
python -V                                              >> "%LOGFILE%" 2>&1
echo WC_SITE=%WC_SITE%                                 >> "%LOGFILE%" 2>&1

REM ---- Decide mode: incremental vs full
SET "UPDATED_PAGES=%ROOT%\ops\updated_pages.txt"
SET "UPDATED_POSTS=%ROOT%\ops\updated_posts.txt"
IF EXIST "%UPDATED_PAGES%" SET "INCR_FLAG=1"
IF EXIST "%UPDATED_POSTS%" SET "INCR_FLAG=1"

IF DEFINED INCR_FLAG GOTO :INCREMENTAL
GOTO :FULL

:INCREMENTAL
echo [INFO] Incremental mode detected.                   >> "%LOGFILE%" 2>&1
IF EXIST "%UPDATED_PAGES%" (
  echo [step] Backfill selected PAGES from %UPDATED_PAGES% >> "%LOGFILE%" 2>&1
  python "%ROOT%\scripts\crawl\backfill_selected_pages.py" --input "%UPDATED_PAGES%"  >> "%LOGFILE%" 2>&1
) ELSE (
  echo [warn] No updated_pages.txt found.                 >> "%LOGFILE%" 2>&1
)
IF EXIST "%UPDATED_POSTS%" (
  echo [step] Backfill selected POSTS from %UPDATED_POSTS% >> "%LOGFILE%" 2>&1
  python "%ROOT%\scripts\crawl\backfill_selected_posts.py" --input "%UPDATED_POSTS%"  >> "%LOGFILE%" 2>&1
) ELSE (
  echo [warn] No updated_posts.txt found.                 >> "%LOGFILE%" 2>&1
)
GOTO :PROCESS

:FULL
echo [step] Crawl full site                              >> "%LOGFILE%" 2>&1
python "%ROOT%\scripts\crawl\crawl_vcm.py"               >> "%LOGFILE%" 2>&1

:PROCESS
echo [step] Preprocess clean                             >> "%LOGFILE%" 2>&1
python "%ROOT%\scripts\processing\preprocess_clean.py"   >> "%LOGFILE%" 2>&1

echo [step] Remove WPBakery/VC shortcodes                >> "%LOGFILE%" 2>&1
python "%ROOT%\scripts\processing\clean_vc_shortcodes.py" >> "%LOGFILE%" 2>&1

echo [step] Normalize page formatting                    >> "%LOGFILE%" 2>&1
python "%ROOT%\scripts\processing\normalize_pages_format.py" >> "%LOGFILE%" 2>&1

echo [step] Normalize product front-matter               >> "%LOGFILE%" 2>&1
python "%ROOT%\scripts\processing\normalize_product_frontmatter.py" >> "%LOGFILE%" 2>&1

echo [step] Detect + inject page videos                  >> "%LOGFILE%" 2>&1
python "%ROOT%\scripts\processing\inject_page_videos.py" >> "%LOGFILE%" 2>&1

echo [step] Add inline videos back into content          >> "%LOGFILE%" 2>&1
python "%ROOT%\scripts\processing\add_inline_videos.py"  >> "%LOGFILE%" 2>&1

echo [step] Export products (WooCommerce API)            >> "%LOGFILE%" 2>&1
python "%ROOT%\scripts\export\export_products.py"        >> "%LOGFILE%" 2>&1

echo [step] Export to Excel workbook                     >> "%LOGFILE%" 2>&1
python "%ROOT%\scripts\export\export_to_workbook.py"     >> "%LOGFILE%" 2>&1

echo [step] Build JSON indexes (pages/posts/products)    >> "%LOGFILE%" 2>&1
python "%ROOT%\scripts\export\build_indexes.py"          >> "%LOGFILE%" 2>&1

IF NOT DEFINED EMB_MODEL SET "EMB_MODEL=all-MiniLM-L6-v2"
echo [step] Build semantic embeddings (model=%EMB_MODEL%) >> "%LOGFILE%" 2>&1
python "%ROOT%\scripts\export\build_embeddings.py" --model "%EMB_MODEL%" >> "%LOGFILE%" 2>&1

echo( >> "%LOGFILE%"
echo [DONE] Audit refresh complete. Log: %LOGFILE%
echo [DONE] Audit refresh complete. Log: %LOGFILE%
GOTO :END_OK

:END_FAIL
echo( 
echo [FAILED] See log (if created): %LOGFILE%
POPD
PAUSE
ENDLOCAL
EXIT /B 1

:END_OK
POPD
PAUSE
ENDLOCAL
EXIT /B 0
