@echo off
title Viral Reel Extractor
cd /d "%~dp0"

echo ========================================================
echo         Launching Viral Reel & Shorts Extractor
echo ========================================================
echo.
echo Starting local web server...
echo Your browser will open automatically in a few seconds.
echo (To stop the app at any time, simply close this window)
echo.

python -m streamlit run app.py --server.headless=false

pause
