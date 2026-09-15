@echo off
setlocal
chcp 874 >nul
set "PYTHONIOENCODING=cp874"
set "BASE_DIR=%~dp0"
set "PYTHON_EXE=C:\Python34\python.exe"
set "CMD_TITLE=AT_POS Robot New Price"
set "CMD_X=800"
set "CMD_Y=0"
set "CMD_WIDTH=600"
set "CMD_HEIGHT=640"
title %CMD_TITLE%

if not exist "%PYTHON_EXE%" (
    echo [ERROR] Python not found: %PYTHON_EXE%
    set "RESULT=1"
    goto :finish
)

if exist "%BASE_DIR%robot" (
    echo [ERROR] Old robot folder structure detected: %BASE_DIR%robot
    echo Please delete the old robot folder before running.
    echo The new project uses: tests\, resources\, libraries\, data\
    set "RESULT=1"
    goto :finish
)

"%PYTHON_EXE%" -c "import ctypes; h=ctypes.windll.user32.FindWindowW(None, '%CMD_TITLE%'); ctypes.windll.user32.MoveWindow(h, %CMD_X%, %CMD_Y%, %CMD_WIDTH%, %CMD_HEIGHT%, True)" >nul 2>&1

if not exist "%BASE_DIR%tests\promotion.robot" (
    echo [ERROR] Robot test not found: %BASE_DIR%tests\promotion.robot
    set "RESULT=1"
    goto :finish
)

if not exist "%BASE_DIR%data\login_credentials.json" (
    echo [ERROR] Credential file not found: %BASE_DIR%data\login_credentials.json
    set "RESULT=1"
    goto :finish
)

"%PYTHON_EXE%" -c "import robot" >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Robot Framework is not installed in %PYTHON_EXE%
    echo Run install_python\install_python.bat first.
    set "RESULT=1"
    goto :finish
)

"%PYTHON_EXE%" -c "import openpyxl" >nul 2>&1
if errorlevel 1 (
    echo [ERROR] openpyxl is not installed in %PYTHON_EXE%
    echo Run install_python\install_python.bat first.
    set "RESULT=1"
    goto :finish
)

if not exist "%BASE_DIR%results" mkdir "%BASE_DIR%results"
"%PYTHON_EXE%" -m robot --outputdir "%BASE_DIR%results" "%BASE_DIR%tests\promotion.robot"
set "RESULT=%ERRORLEVEL%"
if not "%RESULT%"=="0" echo [ERROR] Promotion test failed with code %RESULT%.
if "%RESULT%"=="0" echo [OK] Promotion test completed. See %BASE_DIR%results\report.html and %BASE_DIR%results\log_*.xlsx

:finish
echo.
pause
endlocal & exit /b %RESULT%
