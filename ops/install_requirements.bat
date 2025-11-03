@echo off
setlocal ENABLEEXTENSIONS

REM =============================================
REM  Vericor - Install Python Requirements
REM  Creates/uses venv, upgrades pip, installs -r requirements.txt
REM =============================================

REM -- Move to script folder
cd /d "%~dp0"

REM -- Make sure logs folder exists
if not exist "logs" mkdir "logs"

REM -- Timestamped log file
for /f "tokens=1-4 delims=/ " %%a in ('date /t') do set _DATE=%%d%%b%%c
for /f "tokens=1-2 delims=: " %%a in ('time /t') do set _TIME=%%a%%b
set _TIME=%_TIME::=%
set LOG=logs\install_%_DATE%_%_TIME%.log

echo ============================================================ > "%LOG%"
echo  Vericor - Install Requirements                            >> "%LOG%"
echo  Working dir: %cd%                                         >> "%LOG%"
echo ============================================================ >> "%LOG%"
echo.

REM -- Choose Python (prefer py launcher if available)
where py >nul 2>&1
if %ERRORLEVEL%==0 (
  set PY=py -3
) else (
  set PY=python
)

REM -- Check Python is available
%PY% -V >nul 2>&1
if not %ERRORLEVEL%==0 (
  echo [ERROR] Python not found. Please install Python 3.10+ and re-run.
  echo [ERROR] Python not found.                             >> "%LOG%"
  goto :END
)

REM -- Create venv if missing
if not exist "venv\Scripts\python.exe" (
  echo Creating virtual environment...
  echo Creating virtual environment...                       >> "%LOG%"
  %PY% -m venv venv >> "%LOG%" 2>&1
  if not %ERRORLEVEL%==0 (
    echo [ERROR] Failed to create virtual environment. See %LOG%
    goto :END
  )
)

REM -- Activate venv
call "venv\Scripts\activate"
if not defined VIRTUAL_ENV (
  echo [ERROR] Failed to activate virtual environment.
  echo [ERROR] Failed to activate virtual environment.       >> "%LOG%"
  goto :END
)

REM -- Upgrade pip
echo Upgrading pip...
echo Upgrading pip...                                        >> "%LOG%"
python -m pip install --upgrade pip >> "%LOG%" 2>&1

REM -- Check requirements.txt exists
if not exist "requirements.txt" (
  echo [ERROR] requirements.txt not found in %cd%
  echo [ERROR] requirements.txt not found.                   >> "%LOG%"
  goto :END
)

REM -- Install requirements
echo Installing packages from requirements.txt (this may take a minute)...
echo Installing packages...                                   >> "%LOG%"
pip install -r requirements.txt >> "%LOG%" 2>&1
if not %ERRORLEVEL%==0 (
  echo [ERROR] Package installation failed. See %LOG%
  goto :END
)

echo.
echo ============================================================
echo  ✅ All set! Requirements installed into .\venv
echo  Log written to: %LOG%
echo ============================================================
echo.
goto :PAUSE

:END
echo.
echo ============================================================
echo  ❌ Something went wrong. Check the log:
echo  %LOG%
echo ============================================================
echo.

:PAUSE
pause
endlocal
