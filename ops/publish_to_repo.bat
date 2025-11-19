@echo off
setlocal EnableExtensions EnableDelayedExpansion
pushd "%~dp0\.."

REM ---- Build a nice timestamp for default messages
for /f %%t in ('powershell -NoProfile -Command "Get-Date -Format yyyy-MM-dd_HHmm"') do set "STAMP=%%t"

REM ---- Commit message: use all args if provided; else default
set "MSG=%*"
if "%MSG%"=="" set "MSG=chore: dataset refresh %STAMP%"

REM ---- Stage only intentional files (avoid logs, zips, venv, etc.)
git add ops\*.bat scripts\**\*.py exports\index_*.json exports\embeddings.jsonl .gitignore
if exist README.md git add README.md

REM ---- Commit & push
git commit -m "%MSG%"
if errorlevel 1 goto :end
git push
echo [OK] Published to GitHub with message: %MSG%

:end
popd
endlocal
pause
