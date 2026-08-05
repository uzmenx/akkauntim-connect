@echo off
title AI Trading Bot - Auto Restart Loop
cd /d %~dp0

if exist .venv\Scripts\activate.bat (
    call .venv\Scripts\activate.bat
)

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
