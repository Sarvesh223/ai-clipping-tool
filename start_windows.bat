@echo off
call .venv\Scripts\activate
start "Clip Studio API" cmd /k "cd backend && python -m uvicorn app.main:app --host 127.0.0.1 --port 8000"
start "Clip Studio UI" cmd /k "cd frontend && npm run dev"
timeout /t 6 >nul
start http://127.0.0.1:5173
