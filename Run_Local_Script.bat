@echo off
title Run Local Transcript Analysis
cd /d "%~dp0"

echo ========================================================
echo        Running Local Transcript File Analysis
echo ========================================================
echo.
echo Checking transcript.txt...
echo.

python analyze_local.py

pause
