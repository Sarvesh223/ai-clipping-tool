@echo off
python -m venv .venv || goto :err
call .venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt || goto :err
where node >nul 2>nul || (echo [!] Node.js missing. Install Node 18+ from https://nodejs.org & goto :err)
pushd frontend & call npm install & popd
where ffmpeg >nul 2>nul || echo [!] FFmpeg missing. Run: winget install Gyan.FFmpeg   (then reopen this window)
where ollama >nul 2>nul || echo [!] Ollama missing. Install from https://ollama.com/download then run: ollama pull qwen3:4b
if not exist .env copy .env.example .env
echo.
echo Setup finished. Next: ollama pull qwen3:4b   then run start_windows.bat
exit /b 0
:err
echo Setup failed.
exit /b 1
