@echo off
title Auto Mouse Mover Launcher
cd /d "%~dp0"

:: Use .venv if present
if exist ".venv\Scripts\pythonw.exe" (
    start "" ".venv\Scripts\pythonw.exe" main.py
    exit /b
)
if exist ".venv\Scripts\python.exe" (
    start "" ".venv\Scripts\python.exe" main.py
    exit /b
)

:: Fallback to system pythonw
where pythonw >nul 2>nul
if %ERRORLEVEL% equ 0 (
    start "" pythonw main.py
    exit /b
)

:: Fallback to system python
where python >nul 2>nul
if %ERRORLEVEL% equ 0 (
    start "" python main.py
    exit /b
)

echo [ERROR] Python was not found in your system PATH.
pause
