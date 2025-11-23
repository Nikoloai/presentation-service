@echo off
echo ================================
echo Starting Presentation Service
echo ================================
echo.

REM Check if .env file exists
if not exist .env (
    echo WARNING: .env file not found!
    echo Please create .env file with your API keys
    echo Copy .env.example to .env and add your keys
    echo.
    pause
    exit /b 1
)

echo Starting Flask server...
echo.
echo Access the application at: http://localhost:5000
echo Press Ctrl+C to stop the server
echo.

python app.py

pause
