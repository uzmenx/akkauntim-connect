@echo off
set /p msg="Commit xabarini kiriting (bo'sh qoldirilsa 'chart' deb olinadi): "
if "%msg%"=="" set msg=chart

echo Kodlarni xavfsiz stage qilinmoqda (dist, db, binary fayllardan xoli)...
git add -A -- ":!dist" ":!*.db" ":!*.db-wal" ":!*.db-shm" ":!*.pth" ":!*.zip" ":!*.joblib" ":!node_modules" ":!chroma_db"

echo Commit yaratilmoqda...
git commit -m "%msg%"

echo main branchiga push qilinmoqda...
git push origin main

echo Bajarildi!
pause
