@echo off
cd /d "%~dp0"
title Risk Work Watchdog

:restart
python watchdog.py

echo.
echo Watchdog stopped. Restarting in 10 seconds...
timeout /t 10 /nobreak >nul
goto restart
