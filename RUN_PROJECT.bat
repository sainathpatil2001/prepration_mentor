@echo off
REM Django Examination System - One-Click Setup and Run Script
REM This script sets up the environment and starts the development server

echo.
echo ====================================================================
echo   ONLINE EXAMINATION SYSTEM - Setup and Launch
echo ====================================================================
echo.

REM Get the project directory
cd /d "%~dp0"
set PROJECT_DIR=%cd%

echo [1/4] Activating virtual environment...
call "%PROJECT_DIR%\sai\Scripts\activate.bat"

if errorlevel 1 (
    echo Error: Failed to activate virtual environment
    pause
    exit /b 1
)
echo [✓] Virtual environment activated

echo.
echo [2/4] Installing/Updating Python requirements...
python -m pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet

if errorlevel 1 (
    echo Warning: Some packages may not have installed correctly
)
echo [✓] Requirements installed

echo.
echo [3/4] Running database migrations...
python manage.py migrate --noinput

if errorlevel 1 (
    echo Warning: Migration issues detected (this may be normal on first run)
)
echo [✓] Migrations completed

echo.
echo [4/4] Starting development server...
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

REM Start Django development server
python manage.py runserver 0.0.0.0:8000

pause
