@echo off
setlocal EnableExtensions EnableDelayedExpansion

REM ================================================
REM  VeriCor Crawl + Audit : Refresh Pipeline
REM ================================================

REM -- Normalize to repo root regardless of where it's launched
pushd "%~dp0" >nul
cd ..

set "ROOT=%cd%"
set "OPS=%ROOT%\ops"
set "DATA=%ROOT%\data"
set "LOGDIR=%DATA%\logs"
if not exist "%LOGDIR%" mkdir "%LOGDIR%" >nul 2>&1

for /f "tokens=1-3 delims=/ " %%a in ("%date%") do set "DATESTAMP=%date:~10,4%%date:~4,2%%date:~7,2%"
for /f "tokens=1-3 delims=:." %%h in ("%time%") do set "TIMESTAMP=%time:~0,2%%time:~3,2%%time:~6,2%"
set "TIMESTAMP=%TIMESTAMP: =0%"
set "LOG=%LOGDIR%\refresh_%DATESTAMP%_%TIMESTAMP%.log"

echo ======================================================
echo  VeriCor Crawl + Audit
echo  Root: %ROOT%
echo  Log:  %LOG%
echo ======================================================

REM -- Activate venv
if exist "%ROOT%\venv\Scripts\activate.bat" (
  call "%ROOT%\venv\Scripts\activate.bat"
) else (
  echo [ERROR] Python venv missing at "%ROOT%\venv". Create it with:
  echo         python -m venv venv ^&^& venv\Scripts\activate ^&^& pip install -r env\requirements.txt
  goto :END
)

REM -- Load .env (non-fatal if missing, but warn)
set "ENVFILE=%ROOT%\env\.env"
if exist "%ENVFILE%" (
  for /f "usebackq tokens=1,* delims==#" %%A in ("%ENVFILE%") do (
    if not "%%~A"=="" if not "%%~B"=="" set "%%~A=%%~B"
  )
) else (
  echo [WARN] %ENVFILE% not found. Continuing without env overrides.>>"%LOG%"
)

REM -- Run steps (append output to LOG)
REM (1) Build indexes
echo [STEP] Build JSON indexes >>"%LOG%"
python "scripts\export\build_indexes.py" >>"%LOG%" 2>&1
if errorlevel 1 goto :FAILED

REM (2) Build embeddings (MiniLM default — adjust if you change models)
echo [STEP] Build embeddings >>"%LOG%"
python "scripts\export\build_embeddings.py" --model all-MiniLM-L6-v2 >>"%LOG%" 2>&1
if errorlevel 1 goto :FAILED

REM (3) OPTIONAL: Export workbook (uncomment if you want this every run)
REM echo [STEP] Export workbook >>"%LOG%"
REM python "scripts\export\export_to_workbook.py" >>"%LOG%" 2>&1
REM if errorlevel 1 goto :FAILED

echo.>>"%LOG%"
echo [DONE] Audit refresh complete. Log: %LOG%>>"%LOG%"
echo.
echo [DONE] Audit refresh complete. Log: %LOG%

REM -- Tail last 60 lines so you see progress without opening the file
powershell -NoProfile -Command ^
  "$p='%LOG%'; if(Test-Path $p){Write-Host '--- LOG TAIL ---'; Get-Content $p -Tail 60}"

goto :END

:FAILED
echo.
echo [ERROR] A step failed. See log: %LOG%
powershell -NoProfile -Command "Write-Host '--- LOG TAIL ---'; Get-Content '%LOG%' -Tail 80"
exit /b 1

:END
popd >nul
endlocal
pause
