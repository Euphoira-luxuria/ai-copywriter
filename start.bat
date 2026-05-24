@echo off
cd /d "%~dp0"

if "%DEEPSEEK_API_KEY%"=="" (
    echo [!] 请先设置环境变量 DEEPSEEK_API_KEY
    echo     方法 1（临时）: set DEEPSEEK_API_KEY=sk-xxx ^&^& start.bat
    echo     方法 2（永久）: setx DEEPSEEK_API_KEY sk-xxx
    pause
    exit /b 1
)

python app.py
pause
