*** Settings ***
Documentation     Reusable keywords for the POS login screen.
Library           ../libraries/CoordinateRobot.py    ../data/login_credentials.json

*** Variables ***
${EMPLOYEE_X}    314
${EMPLOYEE_Y}    218
${PASSWORD_X}    314
${PASSWORD_Y}    278
${ENTER_X}       676
${ENTER_Y}       350


*** Keywords ***
Check Store Code Before Login
    Sleep    5s
    ${store_code}=    Get Login Value    store_code
    Should Not Be Empty    ${store_code}
    Log    ตรวจสอบรหัสสาขาเรียบร้อย: ${store_code}

Login With Credentials From Json
    ${employee_code}=    Get Login Value    employee_code
    ${password}=    Get Login Value    password
    Click At    ${EMPLOYEE_X}    ${EMPLOYEE_Y}
    Type Text    ${employee_code}
    Click At    ${PASSWORD_X}    ${PASSWORD_Y}
    Type Text    ${password}
    Press Enter
    ${popup_found}=    Wait For Popup And Press Enter    10    0.5
    Log    พบหน้าต่างแจ้งเตือนการยักยอกทรัพย์: ${popup_found}
    Should Be True    ${popup_found}    เข้าสู่ระบบไม่สำเร็จ: ไม่พบหน้าต่างแจ้งเตือนการยักยอกทรัพย์

Capture Employee Field Coordinate
    ${x}    ${y}=    Capture Current Cursor
    Log    employee: x=${x}, y=${y}

Capture Password Field Coordinate
    ${x}    ${y}=    Capture Current Cursor
    Log    password: x=${x}, y=${y}

Capture Enter Button Coordinate
    ${x}    ${y}=    Capture Current Cursor
    Log    enter: x=${x}, y=${y}