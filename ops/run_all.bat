@echo off
REM One-click wrapper: sets up env then runs the full refresh.
cd /d "%~dp0"

REM 1) Prepare environment quietly (returns to this script)
if exist "start_vericor_env.bat" (
  call start_vericor_env.bat --quiet
) else (
  echo [ERROR] start_vericor_env.bat not found.
  pause
  exit /b 1
)

REM 2) Verify required vars are set
if not defined WC_CK  echo [ERROR] Missing WC_CK & pause & exit /b 1
if not defined WC_CS  echo [ERROR] Missing WC_CS & pause & exit /b 1
if not defined WC_SITE echo [ERROR] Missing WC_SITE & pause & exit /b 1

REM 3) Run the pipeline
if exist "refresh_audit.bat" (
  call refresh_audit.bat --noninteractive
) else (
  echo [ERROR] refresh_audit.bat not found.
  pause
  exit /b 1
)

echo.
echo ✅ All done. See logs in the .\logs folder.
pause
