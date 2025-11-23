@echo off
echo ================================
echo AI Presentation Generator Setup
echo ================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.8+ from https://www.python.org/downloads/
    pause
    exit /b 1
)

echo Python detected:
python --version
echo.

REM Install dependencies
echo Installing dependencies...
pip install -r requirements.txt

if errorlevel 1 (
    echo.
    echo ERROR: Failed to install dependencies
    pause
    exit /b 1
)

echo.
echo ================================
echo Installation complete!
echo ================================
echo.
echo NEXT STEPS:
echo 1. Get API keys:
echo    - OpenAI: https://platform.openai.com/api-keys
echo    - Pexels: https://www.pexels.com/api
echo.
echo 2. Create .env file with your keys:
echo    Copy .env.example to .env and add your keys
echo.
echo 3. Run the application:
echo    python app.py
echo.
echo 4. Open browser:
echo    http://localhost:5000
echo.
pause
