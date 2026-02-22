@echo off
echo Starting AgentOS...

:: Start Backend
start "AgentOS Backend" cmd /k "cd /d %~dp0 && .venv\\Scripts\\python.exe -m uvicorn backend.server:app --reload --port 8000"

:: Start Frontend
start "AgentOS Frontend" cmd /k "cd /d %~dp0frontend && npm run dev"

:: Open Browser (wait a bit)
timeout /t 5
start http://localhost:5173

echo AgentOS is running!
pause
