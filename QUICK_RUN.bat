@echo off
REM Django Examination System - Quick Launch (Assumes already setup)
REM This script only starts the development server (no installation)

echo.
echo ====================================================================
echo   ONLINE EXAMINATION SYSTEM - Quick Launch
echo ====================================================================
echo.

REM Get the project directory
cd /d "%~dp0"
set PROJECT_DIR=%cd%

echo Activating virtual environment...
call "%PROJECT_DIR%\sai\Scripts\activate.bat"

if errorlevel 1 (
    echo Error: Virtual environment not found. Run RUN_PROJECT.bat first
    pause
    exit /b 1
)

echo.
echo ====================================================================
echo   Django Development Server is Starting
echo ====================================================================
echo.
echo Access the application at: http://127.0.0.1:8000
echo Admin panel at: http://127.0.0.1:8000/admin
echo.
echo Press Ctrl+C to stop the server
echo ====================================================================
echo.

python manage.py runserver 0.0.0.0:8000

pause
