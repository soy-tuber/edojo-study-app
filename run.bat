@echo off
rem 江戸女 入試問題 勉強アプリ 起動用
cd /d "%~dp0"
set PY=%LOCALAPPDATA%\Programs\Python\Python312\python.exe
"%PY%" -m streamlit run app.py
pause
