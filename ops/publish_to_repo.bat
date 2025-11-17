@echo off
setlocal
pushd "%~dp0\.."

REM Only stage essential files
git add ops\*.bat scripts\**\*.py exports\index_*.json exports\embeddings.jsonl README.md .gitignore

for /f %%t in ('powershell -NoProfile -Command "Get-Date -Format yyyy-MM-dd_HHmm"') do set "STAMP=%%t"
set "MSG=%~1"
if "%MSG%"=="" set "MSG=chore: dataset refresh (%STAMP%)"

git commit -m "%MSG%" || goto :end
git push
echo [OK] Published to GitHub with message: %MSG%

:end
popd
endlocal
pause
