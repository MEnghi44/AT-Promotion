*** Settings ***
Documentation     ทดสอบเบื้องต้นว่าเครื่อง POS พร้อมใช้งาน Python และ Robot Framework
Library           OperatingSystem
Library           Process

*** Variables ***
${PYTHON_MIN_MAJOR}    3

*** Test Cases ***
Python Should Be Installed
    [Documentation]    ตรวจสอบว่าเรียก python ได้ และแสดงเวอร์ชัน
    ${result}=    Run Process    python    --version    shell=True
    Log    stdout: ${result.stdout} stderr: ${result.stderr}
    Should Be Equal As Integers    ${result.rc}    0

Pip Should Be Available
    [Documentation]    ตรวจสอบว่า pip ใช้งานได้
    ${result}=    Run Process    python    -m    pip    --version    shell=True
    Log    ${result.stdout}
    Should Be Equal As Integers    ${result.rc}    0

Working Folder Should Exist
    [Documentation]    ตรวจสอบว่าโฟลเดอร์ POS หลักมีอยู่จริง
    Directory Should Exist    C:\\AT_POS
