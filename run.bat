@echo off
::
:: Sofware-AI - اسکریپت اجرا برای ویندوز (CMD)
:: این اسکریپت یک virtualenv به نام .venv می‌سازد، وابستگی‌ها را نصب می‌کند،
:: در صورت نبودن، .env را از .env.example می‌سازد و سپس برنامه‌ی اصلی را اجرا می‌کند.

REM --- Create virtual environment if missing ---
if not exist "%~dp0.venv\Scripts\python.exe" (
    echo Creating virtual environment .venv...
    python -m venv "%~dp0.venv" 2>NUL || python3 -m venv "%~dp0.venv"
)

REM --- فعال کردن venv ---
call "%~dp0.venv\Scripts\activate.bat"

echo Using Python: %~dp0.venv\Scripts\python.exe

REM --- ارتقاء pip و نصب الزامات در صورت وجود ---
python -m pip install --upgrade pip
if exist "%~dp0requirements.txt" (
    echo Installing requirements from requirements.txt...
    python -m pip install -r "%~dp0requirements.txt"
)

REM --- در صورت وجود نداشتن، فایل .env را از مثال ایجاد کنید (فایل .env موجود را رونویسی نمی‌کند) ---
if not exist "%~dp0.env" (
    if exist "%~dp0.env.example" (
        copy "%~dp0.env.example" "%~dp0.env" >NUL
        echo Created .env from .env.example. Please edit .env and add real API keys before use.
    ) else (
        echo Warning: .env not found and .env.example not present.
    )
)

REM --- برنامه را اجرا کنید، آرگومان‌ها را ارسال کنید ---
echo Launching application...
python "%~dp0main.py" %*

REM غیرفعال کردن (برای وضوح در جلسات تعاملی)
if defined VIRTUAL_ENV (
    deactivate 2>NUL || REM اگر غیرفعال کردن در دسترس نباشد، غیرفعال می‌شود
)
exit /B %ERRORLEVEL%
