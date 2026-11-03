@echo off
setlocal
cd /d "%~dp0"

echo ===================================================
echo   Finance Tracker Telegram Bot - Windows 11
echo ===================================================

if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] Virtual environment (.venv) belum ditemukan!
    echo Silakan jalankan perintah berikut terlebih dahulu:
    echo   python -m venv .venv
    echo   .venv\Scripts\pip install -r requirements.txt
    pause
    exit /b 1
)

if not exist ".env" (
    echo [INFO] File .env belum ditemukan. Membuat dari .env.example...
    copy .env.example .env
    echo [PERHATIAN] Harap buka file .env dan masukkan BOT_TOKEN Anda sebelum menjalankan bot.
    pause
    exit /b 1
)

echo [INFO] Menjalankan bot...
.venv\Scripts\python.exe -m app
pause

