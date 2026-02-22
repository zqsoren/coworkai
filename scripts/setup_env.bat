@echo off
echo [AgentOS] Setting up environment...

cd /d "%~dp0.."

:: 1. Create venv if not exists
if not exist .venv (
    echo [AgentOS] Creating virtual environment...
    python -m venv .venv
) else (
    echo [AgentOS] Virtual environment already exists.
)

:: 2. Activate
call .venv\Scripts\activate

:: 3. Install dependencies
echo [AgentOS] Installing dependencies from requirements.txt...
pip install -r requirements.txt
pip install -U pip

:: 4. Install Playwright browsers
echo [AgentOS] Installing Playwright browsers (Chromium only)...
playwright install chromium

echo.
echo [AgentOS] Setup execution complete.
echo You can run the app with:
echo .venv\Scripts\streamlit run src/app.py
pause
