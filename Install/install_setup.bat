@echo off
cd /d "%~dp0"

REM เรียกตัวเองซ้ำหนึ่งรอบโดย redirect output ทั้งหมดไปเก็บที่ไฟล์ log ด้วย (นอกเหนือจากที่ยังโชว์
REM บนหน้าจอตามปกติหลังรันจบ) ใช้ตัวแปร LOGGED กันไม่ให้วนเรียกตัวเองไม่รู้จบ
REM
REM หมายเหตุ: เคยลองส่ง output ผ่าน PowerShell Tee-Object เพื่อให้โชว์สดระหว่างรันไปด้วย แต่ทำให้
REM ข้อความภาษาไทยในไฟล์ log เพี้ยน (cmd กับ PowerShell คนละ codepage กัน) จึงใช้วิธีนี้แทน
REM ซึ่งโชว์ผลทั้งหมดทีเดียวหลังรันจบ แต่ข้อความในไฟล์ log ถูกต้องเสมอ
if not defined LOGGED (
    set "LOGGED=1"
    call "%~f0" > "install_setup.log" 2>&1
    type "install_setup.log"
    exit /b
)

echo === ตรวจสอบ Python ===
REM ห้ามเช็คจาก errorlevel ของ "python --version" ตรงๆ เพราะเจอเคสจริงว่า Windows App Execution
REM Alias (ตัวชี้ python.exe ปลอมที่ Windows สร้างเองตอนไม่มี Python จริง) คืน errorlevel 0
REM (สำเร็จ) เสมอ ถึงจะ print ข้อความ error ออกมาก็ตาม (เช่น "[ERROR] Failed to launch...")
REM ต้องเช็คจากเนื้อหา output แทนว่าขึ้นต้นด้วยคำว่า "Python " จริงไหมถึงจะนับว่าเจอ Python ใช้งานได้
set "PYVER="
for /f "delims=" %%v in ('python --version 2^>^&1') do set "PYVER=%%v"
echo %PYVER% | findstr /b /c:"Python " >nul
if errorlevel 1 (
    echo ไม่พบ Python กำลังติดตั้งอัตโนมัติจากไฟล์ที่แนบมากับโปรเจกต์...
    ..\tools\python-installer\python-3.14.5-amd64.exe /quiet InstallAllUsers=0 PrependPath=1 Include_test=0
    echo ติดตั้ง Python เสร็จแล้ว
    REM PATH ที่ installer อัปเดตจะยังไม่มีผลกับ cmd หน้าต่างนี้ (ต้องเปิด cmd ใหม่ถึงจะเห็น python
    REM ได้ตรงๆ) จึงเรียกผ่าน path เต็มของ python.exe ที่เพิ่งติดตั้งไปแทน (per-user install
    REM ลงที่ %LocalAppData%\Programs\Python\Python314 เสมอ) เพื่อไปต่อขั้นตอนติดตั้ง package
    REM ในสคริปต์เดียวกันนี้ได้เลย ไม่ต้องให้ปิด-เปิดหน้าต่างใหม่
    set "PYTHON_EXE=%LocalAppData%\Programs\Python\Python314\python.exe"
) else (
    set "PYTHON_EXE=python"
)

echo === ติดตั้ง Python packages (robotframework, rpaframework-windows, pytesseract, pillow, requests) ===
"%PYTHON_EXE%" -m pip install -r requirements.txt

echo === ตรวจสอบ UltraVNC Viewer ===
if not exist "C:\Program Files\uvnc bvba\UltraVNC\vncviewer.exe" (
    echo [คำเตือน] ไม่พบ UltraVNC Viewer ที่ C:\Program Files\uvnc bvba\UltraVNC\vncviewer.exe
    echo ต้องติดตั้งเองก่อนจาก https://uvnc.com/ แล้วแก้ path ที่คีย์ VNC ใน data\pos_data.json ให้ตรงกับที่ติดตั้งจริง
) else (
    echo พบ UltraVNC Viewer แล้ว
)

echo === เสร็จสิ้น ===
echo (Tesseract-OCR และตัวติดตั้ง Python ไม่ต้องดาวน์โหลดเพิ่ม เพราะอยู่ในโฟลเดอร์ tools\ ของโปรเจกต์นี้แล้ว
echo  ถ้าย้ายเครื่อง ให้คัดลอกทั้งโฟลเดอร์โปรเจกต์ไปด้วย รวมโฟลเดอร์ tools\ และ data\ ด้วย)
