@echo off
setlocal

cd /d "%~dp0"
set "PYTHONUTF8=1"

if exist ".venv\Scripts\python.exe" (
    set "PYTHON_EXE=.venv\Scripts\python.exe"
) else (
    set "PYTHON_EXE=python"
)

"%PYTHON_EXE%" -m streamlit run app.py

if errorlevel 1 (
    echo.
    echo Chuong trinh dung voi loi. Nhan phim bat ky de dong cua so.
    pause >nul
)
