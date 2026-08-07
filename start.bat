@echo off
title AI Trading Bot - Auto Restart Loop
cd /d %~dp0

if exist .venv\Scripts\activate.bat (
    call .venv\Scripts\activate.bat
)

echo ===================================================
echo [INFO] API serveri ishga tushirilmoqda (Port: 8000)...
echo ===================================================
start "AI Bot API Server" /min .venv\Scripts\uvicorn.exe bot.api.main:app --host 127.0.0.1 --port 8000

:loop
echo ===================================================
echo [%date% %time%] Bot ishga tushirilmoqda...
echo ===================================================
python bot_manager.py
echo.
echo ===================================================
echo [WARNING] Bot to'xtadi yoki xatolik berdi!
echo 10 soniyadan so'ng avtomatik qayta ishga tushadi...
echo ===================================================
timeout /t 10
goto loop
