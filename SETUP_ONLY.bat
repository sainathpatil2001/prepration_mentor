@echo off
REM Django Examination System - Setup Only (Without Running Server)
REM This script installs requirements and runs migrations

echo.
echo ====================================================================
echo   ONLINE EXAMINATION SYSTEM - Setup Only
echo ====================================================================
echo.

REM Get the project directory
cd /d "%~dp0"
set PROJECT_DIR=%cd%

echo [1/3] Activating virtual environment...
call "%PROJECT_DIR%\sai\Scripts\activate.bat"

if errorlevel 1 (
    echo Error: Failed to activate virtual environment
    pause
    exit /b 1
)
echo [✓] Virtual environment activated

echo.
echo [2/3] Installing/Updating Python requirements...
python -m pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet

if errorlevel 1 (
    echo Warning: Some packages may not have installed correctly
)
echo [✓] Requirements installed

echo.
echo [3/3] Running database migrations...
python manage.py migrate --noinput

if errorlevel 1 (
    echo Warning: Migration issues detected
)
echo [✓] Migrations completed

echo.
echo ====================================================================
echo   Setup Complete!
echo ====================================================================
echo.
echo Next steps:
echo - Run 'RUN_PROJECT.bat' to start the development server
echo - Or run: python manage.py runserver
echo.
pause
