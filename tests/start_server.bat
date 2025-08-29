@echo off
echo ========================================
echo   Steem/Hive Curation Test Interface
echo ========================================
echo.
echo Starting web server...
echo Access the interface at: http://localhost:5001
echo Press Ctrl+C to stop the server
echo.

cd /d "%~dp0"
python app.py

pause
