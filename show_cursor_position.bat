@echo off
setlocal
set "BASE_DIR=%~dp0"
set "PYTHON_EXE=C:\Python34\python.exe"

if not exist "%PYTHON_EXE%" (
    echo [ERROR] Python not found: %PYTHON_EXE%
    pause
    exit /b 1
)

"%PYTHON_EXE%" "%BASE_DIR%show_cursor_position.py"
endlocal
