@echo off
title ETS2 Phone Controller

:: Re-launch this file as Administrator if it is not already (ETS2 and this must match).
net session >nul 2>&1
if %errorlevel% neq 0 (
    powershell -NoProfile -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
    exit /b
)

:: An elevated window starts in System32, so go to this file's own folder first.
cd /d "%~dp0"

call venv\Scripts\activate
python server.py %*

:: Keep the window open if the server stops or crashes, so the error stays readable.
pause
