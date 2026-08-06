@echo off
title AI Trading Bot - O'rnatish
echo ===================================================
echo Yangi kompyuter uchun o'rnatish jarayoni boshlandi...
echo ===================================================

echo 1. Python virtual muhit (.venv) yaratilmoqda...
python -m venv .venv

echo 2. Virtual muhit faollashtirilmoqda va Python paketlari o'rnatilmoqda...
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r bot_requirements.txt

echo 3. Frontend paketlari (Node.js) o'rnatilmoqda...
call npm install

echo ===================================================
echo [MUVAFFAQIYATLI] Barcha paketlar o'rnatildi!
echo ===================================================
echo Botni ishga tushirish uchun "start.bat" ni bosing.
echo ===================================================
pause
