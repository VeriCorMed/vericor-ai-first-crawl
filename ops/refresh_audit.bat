@echo off
setlocal EnableExtensions EnableDelayedExpansion

REM ======================================================
REM  VeriCor Crawl + Audit : Refresh Pipeline
REM  Usage: ops\refresh_audit.bat [FULL|FAST]
REM    FULL (default): indexes + embeddings
REM    FAST: indexes only (skips embeddings)
REM ======================================================

REM -- Normalize to repo root no matter where it's launched
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

set "MODE=%~1"
if /I "%MODE%"==""    set "MODE=FULL"
if /I "%MODE%"=="ALL" set "MODE=FULL"

echo ======================================================
echo  VeriCor Crawl + Audit
echo  Root: %ROOT%
echo  Log:  %LOG%
echo  Mode: %MODE%
echo ======================================================

REM -- Activate venv
if exist "%ROOT%\venv\Scripts\activate.bat" (
  call "%ROOT%\venv\Scripts\activate.bat"
) else (
  echo [ERROR] Python venv missing at "%ROOT%\venv". Create it with:>>"%LOG%"
  echo python -m venv venv ^&^& venv\Scripts\activate ^&^& pip install -r env\requirements.txt>>"%LOG%"
  echo [ERROR] Python venv missing. See log: %LOG%
  goto :ENDFAIL
)

REM -- Sanity: show python path to ensure venv is active
where python 1>>"%LOG%" 2>&1
python -V  1>>"%LOG%" 2>&1

REM -- Load .env (non-fatal if missing)
set "ENVFILE=%ROOT%\env\.env"
if exist "%ENVFILE%" (
  for /f "usebackq tokens=1,* delims==#" %%A in ("%ENVFILE%") do (
    if not "%%~A"=="" if not "%%~B"=="" set "%%~A=%%~B"
  )
) else (
  echo [WARN] %ENVFILE% not found. Continuing without env overrides.>>"%LOG%"
)

REM -- (1) Build indexes
echo [STEP] Build JSON indexes>>"%LOG%"
python "scripts\export\build_indexes.py" 1>>"%LOG%" 2>&1
if errorlevel 1 goto :FAILED

REM -- (2) Embeddings unless FAST mode
if /I not "%MODE%"=="FAST" (
  echo [STEP] Build embeddings (all-MiniLM-L6-v2)>>"%LOG%"
  python "scripts\export\build_embeddings.py" --model all-MiniLM-L6-v2 1>>"%LOG%" 2>&1
  if errorlevel 1 goto :FAILED
)

REM -- (3) OPTIONAL workbook (uncomment to enable)
REM echo [STEP] Export workbook>>"%LOG%"
REM python "scripts\export\export_to_workbook.py" 1>>"%LOG%" 2>&1
REM if errorlevel 1 goto :FAILED

echo.>>"%LOG%"
echo [DONE] Audit refresh complete. Log: %LOG%>>"%LOG%"
echo.
echo [DONE] Audit refresh complete. Log: %LOG%

REM -- Tail last 60 lines if PowerShell available
where powershell >nul 2>&1 && powershell -NoProfile -Command ^
  "$p='%LOG%'; if(Test-Path $p){Write-Host '--- LOG TAIL ---'; Get-Content $p -Tail 60}"

goto :ENDOK

:FAILED
echo.
echo [ERROR] A step failed. See log: %LOG%
where powershell >nul 2>&1 && powershell -NoProfile -Command ^
  "Write-Host '--- LOG TAIL ---'; Get-Content '%LOG%' -Tail 100"
goto :ENDFAIL

:ENDOK
popd >nul
endlocal
pause
exit /b 0

:ENDFAIL
popd >nul
endlocal
pause
exit /b 1
