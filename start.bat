@echo off
chcp 65001 > nul
echo Запускаю скрипт...
timeout /t 3 >nul
python main.py
pause