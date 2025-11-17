@echo off
setlocal
pushd "%~dp0\.."

REM Only stage intentional files
git add ops\*.bat scripts\**\*.py exports\index_*.json exports\embeddings.jsonl .gitignore
if exist README.md git add README.md

REM Build message from all args; if none, prompt
set "MSG=%*"
if "%MSG%"=="" (
  for /f %%t in ('powershell -NoProfile -Command "Get-Date -Format yyyy-MM-dd_HHmm"') do set "STAMP=%%t"
  set /p MSG=Commit message [default: chore: dataset refresh (%STAMP%) ]: 
  if "%MSG%"=="" set "MSG=chore: dataset refresh (%STAMP%)"
)

git commit -m "%MSG%"
if errorlevel 1 goto :end

git push
echo [OK] Published to GitHub with message: %MSG%

:end
popd
endlocal
pause
