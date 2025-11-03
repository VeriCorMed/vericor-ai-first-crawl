@echo off
REM ======================================================
REM  start_vericor_env.bat
REM  Opens a command window with venv activated and ready
REM ======================================================

SETLOCAL ENABLEDELAYEDEXPANSION

REM -- Resolve project root (parent of /ops)
SET "SCRIPT_DIR=%~dp0"
PUSHD "%SCRIPT_DIR%\.."
SET "ROOT=%CD%"

TITLE VeriCor Crawl Environment

ECHO [INFO] Project root: %ROOT%

REM -- Use venv at root (your confirmed setup)
IF EXIST "%ROOT%\venv\Scripts\activate.bat" (
    SET "VENV_PATH=%ROOT%\venv"
) ELSE (
    ECHO [ERROR] No virtual environment found at %ROOT%\venv
    ECHO Create one with: python -m venv venv
    POPD
    PAUSE
    EXIT /B 1
)

REM -- Activate venv
CALL "%VENV_PATH%\Scripts\activate.bat"
IF ERRORLEVEL 1 (
    ECHO [ERROR] Failed to activate virtual environment.
    POPD
    PAUSE
    EXIT /B 1
)

REM -- Load .env (from root or env\.env)
SET "ENV_FILE="
IF EXIST "%ROOT%\.env"     SET "ENV_FILE=%ROOT%\.env"
IF EXIST "%ROOT%\env\.env" SET "ENV_FILE=%ROOT%\env\.env"
IF DEFINED ENV_FILE (
    FOR /F "usebackq tokens=1* delims== eol=#" %%A IN ("%ENV_FILE%") DO (
        IF NOT "%%~A"=="" SET "%%A=%%B"
    )
    ECHO [INFO] Loaded environment vars from %ENV_FILE%
) ELSE (
    ECHO [WARN] .env not found in root or env folder.
)

ECHO.
ECHO [ENVIRONMENT READY]
ECHO Python version:
python -V
ECHO.
ECHO You are now in the VeriCor Crawl environment.
ECHO Type ^<python scriptname.py^> or run ops\refresh_audit.bat
ECHO.

POPD

REM --- Keep this window open for user interaction ---
CMD /K "TITLE VeriCor Crawl Env & PROMPT $P$G"
