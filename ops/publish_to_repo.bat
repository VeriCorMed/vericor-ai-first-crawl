@echo off
setlocal EnableExtensions EnableDelayedExpansion
pushd "%~dp0\.."

REM ---- Timestamp for default commit message
for /f %%t in ('powershell -NoProfile -Command "Get-Date -Format yyyy-MM-dd_HHmm"') do set "STAMP=%%t"

REM ---- Commit message: all args or default
set "MSG=%*"
if "%MSG%"=="" set "MSG=chore: dataset refresh %STAMP%"

REM ---- Stage only intentional files
git add ops\*.bat scripts\**\*.py exports\index_*.json exports\embeddings.jsonl .gitignore
if exist README.md git add README.md

REM ---- Remove any stale index entries for accidental paths (quiet)
git rm -r --cached "ops/pages_clean" 2>nul 1>nul

REM ---- Commit & push
git commit -m "%MSG%"
if errorlevel 1 goto :END
git push
echo [OK] Published to GitHub with message: %MSG%

:END
popd
endlocal
pause
