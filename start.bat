@echo off
title AI Trading Bot - Auto Restart Loop
cd /d %~dp0

:loop
echo ===================================================
echo [%date% %time%] Bot ishga tushirilmoqda...
echo ===================================================
python run_bot.py
echo.
echo ===================================================
echo [WARNING] Bot to'xtadi yoki xatolik berdi!
echo 10 soniyadan so'ng avtomatik qayta ishga tushadi...
echo ===================================================
timeout /t 10
goto loop
