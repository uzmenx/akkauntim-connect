@echo off
set /p msg="Commit xabarini kiriting (bo'sh qoldirilsa 'update' deb olinadi): "
if "%msg%"=="" set msg=update

echo Kodlarni stage qilinmoqda...
git add .gitignore src/ supabase/

echo Commit yaratilmoqda...
git commit -m "%msg%"

echo Hozirgi branch aniqlanmoqda...
for /f "tokens=*" %%i in ('git branch --show-current') do set branch=%%i

echo %branch% branchiga push qilinmoqda...
git push origin %branch%

echo Bajarildi!
pause
