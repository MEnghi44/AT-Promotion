@echo off
REM ============================================================
REM  Setup Python + Robot Framework on POS machine (Windows XP)
REM  1) Install Python from local installer (offline)
REM  2) Install/upgrade pip and robotframework (offline)
REM  3) Run Robot Framework test
REM ============================================================
setlocal

set "BASE_DIR=%~dp0"
set "INSTALLER_NAME=python-3.4.4.msi"
set "INSTALLER_PATH=%BASE_DIR%installer\%INSTALLER_NAME%"
set "PYTHON_DIR=C:\Python34"
set "PYTHON_EXE=%PYTHON_DIR%\python.exe"
set "PACKAGES_DIR=%BASE_DIR%packages"
set "TEST_FILE=%BASE_DIR%tests\test_pos.robot"

echo ============================================
echo  Step 1: Install Python
echo ============================================

if not exist "%INSTALLER_PATH%" (
    echo [ERROR] Installer not found: %INSTALLER_PATH%
    pause
    exit /b 1
)

if exist "%PYTHON_EXE%" (
    echo Python already installed at %PYTHON_DIR%, skipping install.
) else (
    echo Installing Python from %INSTALLER_PATH% ...
    msiexec /i "%INSTALLER_PATH%" /qn ALLUSERS=1 ADDLOCAL=ALL TARGETDIR="%PYTHON_DIR%"
    if errorlevel 1 (
        echo [ERROR] Python install failed.
        pause
        exit /b 1
    )
)

if not exist "%PYTHON_EXE%" (
    echo [ERROR] Python executable not found at %PYTHON_EXE%
    pause
    exit /b 1
)

"%PYTHON_EXE%" -c "import sys; print(sys.executable); print(sys.version)"
set "PATH=%PYTHON_DIR%;%PYTHON_DIR%\Scripts;%PATH%"
echo Python 3.4 is ready. Continuing to offline package setup...

echo.
echo ============================================
echo  Step 2: Install pip + robotframework (offline)
echo ============================================

if not exist "%PACKAGES_DIR%" (
    echo [ERROR] Packages folder not found: %PACKAGES_DIR%
    pause
    exit /b 1
)

"%PYTHON_EXE%" -m pip --version >nul 2>&1
if errorlevel 1 (
    echo [WARN] Python 3.4 pip is broken or missing. Removing the broken pip first.
    if exist "%PYTHON_DIR%\Lib\site-packages\pip" rmdir /s /q "%PYTHON_DIR%\Lib\site-packages\pip"
    for /d %%D in ("%PYTHON_DIR%\Lib\site-packages\pip-*.dist-info") do rmdir /s /q "%%~D"
    REM leftover pip-*.egg เช่น pip-18.1-py3.4.egg จากการติดตั้งแบบ
    REM easy_install ครั้งก่อน ทำให้ ensurepip --upgrade ด้านล่างเห็นว่า
    REM pip ทันสมัยอยู่แล้ว แล้วข้ามการติดตั้งจริง ผลคือ pip ยังใช้งาน
    REM ไม่ได้ ต้องลบทั้งไฟล์/โฟลเดอร์ egg และ path
    REM reference ใน easy-install.pth ออกก่อน ไม่งั้น ensurepip จะไม่ยอม
    REM ติดตั้ง pip ใหม่ให้จริงๆ
    if exist "%PYTHON_DIR%\Lib\site-packages\pip-18.1-py3.4.egg" rmdir /s /q "%PYTHON_DIR%\Lib\site-packages\pip-18.1-py3.4.egg" 2>nul
    if exist "%PYTHON_DIR%\Lib\site-packages\pip-18.1-py3.4.egg" del /q "%PYTHON_DIR%\Lib\site-packages\pip-18.1-py3.4.egg" 2>nul
    for /d %%D in ("%PYTHON_DIR%\Lib\site-packages\pip-*.egg") do rmdir /s /q "%%~D" 2>nul
    for %%F in ("%PYTHON_DIR%\Lib\site-packages\pip-*.egg") do del /q "%%~F" 2>nul
    if exist "%PYTHON_DIR%\Scripts\pip.exe" del /q "%PYTHON_DIR%\Scripts\pip.exe"
    if exist "%PYTHON_DIR%\Scripts\pip3.exe" del /q "%PYTHON_DIR%\Scripts\pip3.exe"
    if exist "%PYTHON_DIR%\Scripts\pip3.4.exe" del /q "%PYTHON_DIR%\Scripts\pip3.4.exe"
    if exist "%PYTHON_DIR%\Lib\site-packages\easy-install.pth" (
        findstr /v /i "pip-" "%PYTHON_DIR%\Lib\site-packages\easy-install.pth" > "%PYTHON_DIR%\Lib\site-packages\easy-install.pth.tmp"
        move /y "%PYTHON_DIR%\Lib\site-packages\easy-install.pth.tmp" "%PYTHON_DIR%\Lib\site-packages\easy-install.pth" >nul
    )
    "%PYTHON_EXE%" -m ensurepip --upgrade
    if errorlevel 1 (
        echo [ERROR] ensurepip failed.
        pause
        exit /b 1
    )
)

REM pip ตัว bootstrap จาก ensurepip (Python 3.4) เป็นเวอร์ชันเก่ามาก
REM ยังไม่รู้จัก --disable-pip-version-check (flag นี้เพิ่มมาทีหลังใน
REM pip รุ่นใหม่) เลยห้ามใส่ตอนอัปเกรด pip ครั้งแรกนี้ - ใส่ได้แค่ตอน
REM เรียก pip 19.1.1 ที่อัปเกรดแล้วในขั้นต่อไปเท่านั้น
"%PYTHON_EXE%" -m pip install --no-index --find-links="%PACKAGES_DIR%" --upgrade "%PACKAGES_DIR%\pip-19.1.1-py2.py3-none-any.whl"
REM pip 19.1.1 บน Windows XP มัก crash ตอน cleanup temp build dir ของ
REM ตัวเอง (PermissionError: ไฟล์ถูกล็อกโดยโปรเซสอื่น) ทั้งที่ pip
REM เวอร์ชันใหม่ถูกติดตั้งสำเร็จไปแล้วก่อนจะ crash ตอน cleanup - ถือว่า
REM errorlevel จากบรรทัดนี้เชื่อไม่ได้เสมอไป ต้องเช็คซ้ำว่า pip ใช้งาน
REM ได้จริงหรือไม่แทนการเชื่อ errorlevel ตรงๆ
"%PYTHON_EXE%" -m pip --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] pip upgrade failed.
    pause
    exit /b 1
)

"%PYTHON_EXE%" -m pip install --disable-pip-version-check --no-index --find-links="%PACKAGES_DIR%" robotframework==3.1.2
if errorlevel 1 (
    echo [ERROR] robotframework install failed.
    pause
    exit /b 1
)

echo.
echo ============================================
echo  Step 2b: Install New Price test dependencies (offline)
echo    openpyxl (Excel log), pyodbc (SQL Server - reads actual sale
echo    totals from POSG2 instead of reading the POS screen)
echo ============================================

"%PYTHON_EXE%" -m pip install --disable-pip-version-check --no-index --find-links="%PACKAGES_DIR%" openpyxl==2.4.9
if errorlevel 1 (
    echo [ERROR] openpyxl install failed.
    pause
    exit /b 1
)

"%PYTHON_EXE%" -m pip install --disable-pip-version-check --no-index --find-links="%PACKAGES_DIR%" pyodbc==4.0.27
if errorlevel 1 (
    echo [ERROR] pyodbc install failed.
    pause
    exit /b 1
)

echo.
echo ============================================
echo  Step 3: Run Robot Framework test
echo ============================================

if not exist "%TEST_FILE%" (
    echo [ERROR] Test file not found: %TEST_FILE%
    pause
    exit /b 1
)

"%PYTHON_EXE%" -m robot --outputdir "%BASE_DIR%results" "%TEST_FILE%"

echo.
echo Done. See results at %BASE_DIR%results\report.html
pause
endlocal
