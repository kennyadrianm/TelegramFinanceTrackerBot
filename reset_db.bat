@echo off
setlocal
cd /d "%~dp0"

echo ===================================================
echo   Reset Database Finance Tracker Bot
echo ===================================================
echo PERINGATAN: Seluruh data transaksi, user, dan kategori
echo kustom akan dihapus secara permanen!
echo.
set /p confirm="Apakah Anda yakin ingin reset database? (y/n): "
if /i not "%confirm%"=="y" (
    echo Operasi dibatalkan.
    pause
    exit /b 0
)

echo.
.venv\Scripts\python.exe reset_db.py
pause

