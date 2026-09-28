@echo off
title KALL // CLASSIFIED MILLIMETER-WAVE HOLOGRAPHIC DEFENSE PORTAL
cls
echo ===============================================================================
echo   KALL // CLASSIFIED MILLIMETER-WAVE HOLOGRAPHIC DEFENSE SYSTEM
echo   SECURITY CLASSIFICATION: TOP SECRET // NOFORN // SPECIAL ACCESS REQUIRED
echo ===============================================================================
echo.
echo Launching KALL Tactical Surveillance Console...
echo.

cd /d "%~dp0"
python run_kall.py --port 8080

pause
