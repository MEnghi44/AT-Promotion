*** Settings ***
Documentation     Keyword สำหรับ flow ทดสอบโปรโมชัน "New Price" บนหน้าจอ POS
...               ลอจิกหลักของแต่ละแถว (สแกน/Add/สมาชิก/เช็คราคา/ยืนยัน) อยู่ใน
...               NewPriceRobot.py (Robot Framework 3.1.2 ไม่มี IF/ELSE block
...               เขียนเงื่อนไขพวกนี้ใน Python จะง่ายกว่า)
...               พิกัดหน้าจอเก็บไว้เป็น Variables ในไฟล์นี้ (แบบเดียวกับ
...               login_keywords.robot) ไม่ได้เก็บใน login_credentials.json
Library           ../libraries/CoordinateRobot.py    ../data/login_credentials.json
Library           ../libraries/NewPriceRobot.py    ../data/login_credentials.json

*** Variables ***
# กรอกค่าพิกัดตรงนี้ โดยใช้ show_cursor_position.bat หรือ keyword Capture
# *Coordinate ด้านล่าง เอาเมาส์ไปวางที่ปุ่ม/ช่องจริงบนเครื่อง POS ก่อน
# ค่า 0/0 แปลว่า "ยังไม่ได้ calibrate"
${BARCODE_INPUT_X}                  17
${BARCODE_INPUT_Y}                  58
${MEMBER_BUTTON_X}                  725
${MEMBER_BUTTON_Y}                  82
${MEMBER_BARCODE_INPUT_X}           50
${MEMBER_BARCODE_INPUT_Y}           150
${MEMBER_WELCOME_CONFIRM_X}         720
${MEMBER_WELCOME_CONFIRM_Y}         515

# จุดบนหัวข้อสีเขียว "ยินดีต้อนรับสมาชิก ALL member ..." ด้านบนหน้านั้น ใช้
# ตรวจสอบว่ากดยืนยันผ่านแล้วจริง (ออกจากหน้านี้แล้ว) ก่อนไปขั้นตอนถัดไป
${MEMBER_WELCOME_HEADER_X}          15
${MEMBER_WELCOME_HEADER_Y}          15

${RECEIVE_EXACT_BUTTON_X}           575
${RECEIVE_EXACT_BUTTON_Y}           240
${POPUP_CONFIRM_YES_X}              320
${POPUP_CONFIRM_YES_Y}              350

# จุดที่อยู่ "บนตัวเลขราคา" — อ่านข้อความจริงจากตัวควบคุมของโปรแกรม POS
# ตรงๆ ผ่าน Windows API (ไม่ใช้ OCR) วางเมาส์ตรงกลางตัวเลข "ยอดที่ต้องชำระ"
# แล้วอ่านค่า x,y มากรอก
${PRICE_DISPLAY_X}                  363
${PRICE_DISPLAY_Y}                  215

# จุดปุ่ม "1. Sign Off" บนหน้าเมนูที่ขึ้นมาหลังกด Esc - กดปิดตอนจบทุกแถวแล้ว
${SIGN_OFF_BUTTON_X}                 400
${SIGN_OFF_BUTTON_Y}                 186

# จุดบนพื้นสีเหลืองของ popup "[POSW01040002] รหัสบาร์โค้ดไม่ถูกต้อง" ที่ขึ้น
# หลังพิมพ์บาร์โค้ดแล้ว Enter (ก่อนกด Add) - ใช้เช็คสีพิกเซลว่า popup นี้
# ขึ้นมาไหม ยังไม่ได้ calibrate (0/0) - ฟีเจอร์นี้จะยังไม่ทำงานจนกว่าจะตั้ง
# ค่าจริง (ใช้ keyword Capture Invalid Barcode Popup Point ด้านล่าง)
${INVALID_BARCODE_POPUP_X}          220
${INVALID_BARCODE_POPUP_Y}          240

# จุดบนพื้นสีเหลืองของ popup "[POSW02040103] สอบถามลูกค้าว่าต้องการรับ
# M-Stamp หรือแสตมป์" ที่ขึ้นหลังกด "ใช่" ยืนยัน popup รับพอดี - ใช้เช็คสี
# พิกเซลว่า popup นี้ขึ้นมาไหม ยังไม่ได้ calibrate (0/0) - ฟีเจอร์นี้จะยัง
# ไม่ทำงานจนกว่าจะตั้งค่าจริง (ใช้ keyword Capture M-Stamp Popup Check
# Point ด้านล่าง)
${MSTAMP_POPUP_CHECK_X}             220
${MSTAMP_POPUP_CHECK_Y}             240

# จุดปุ่ม "M-Stamp" บน popup ข้างต้น - กดเลือก M-Stamp เสมอเมื่อ popup นี้
# ขึ้นมา (ใช้ keyword Capture M-Stamp Button Coordinate ด้านล่าง)
${MSTAMP_BUTTON_X}                  320
${MSTAMP_BUTTON_Y}                  350

# เวลาหน่วง (วินาที) ระหว่างทุกขั้นตอน (พิมพ์บาร์โค้ด, กด Add, กดปุ่มต่างๆ,
# รอ popup, รอกลับมาหน้าพร้อมสแกน ฯลฯ) ปรับตรงนี้ที่เดียวมีผลทั้งหมด
${STEP_DELAY_SECONDS}               4

# เวลารอ (วินาที) ก่อนเริ่มอ่านราคาจาก database - เผื่อ database บันทึก
# รายการช้ากว่าที่หน้าจอ POS แสดงผล
${DB_PRICE_CHECK_WAIT_SECONDS}      10

# เวลา timeout สูงสุด (วินาที) ที่จะรอ poll หา COMMON_TRN_NO ใหม่ใน
# database ก่อนจะถือว่าไม่เจอแล้ว fail
${DB_PRICE_CHECK_TIMEOUT_SECONDS}   30

# เวลา timeout สูงสุด (วินาที) ที่จะรอ poll หาข้อมูลจาก TA_PROMOTION_HITRULE
# /TA_PROMOTION_ITEM (ช้ากว่า TS_SALE_ITEM) - ถ้าไม่เจอจน timeout จะบันทึก
# คอลัมน์ lpe_*/item_* เป็นค่าว่าง แต่ไม่ทำให้แถวนั้น fail
${LPE_CHECK_TIMEOUT_SECONDS}        30

# เวลา timeout สูงสุด (วินาที) ที่จะรอปุ่ม "ใช่" ของ popup ยืนยันปรากฏขึ้น
# หลังกดปุ่ม "รับพอดี" - ถ้าไม่ขึ้นจน timeout จะถือว่า fail ("Popup ไม่เด้ง")
${POPUP_TIMEOUT_SECONDS}            30

# จำนวนครั้งที่จะ "ลองคลิกปุ่มรับพอดีซ้ำ" ถ้า popup ยืนยันยังไม่เด้งขึ้นมา
# ภายใน POPUP_TIMEOUT_SECONDS (เผื่อ POS ตอบสนองช้ากว่าปกติชั่วคราว) - ค่า
# 1 หมายถึงลองซ้ำ 1 ครั้ง (รวมครั้งแรกเป็น 2 ครั้ง) ก่อนถือว่า fail จริง
${RECEIVE_EXACT_RETRY_COUNT}        1

*** Keywords ***
# ใช้ชื่อเต็ม NewPriceRobot.xxx (ไม่ใช่แค่ "Set New Price Coordinate" เฉยๆ)
# เพราะ FreeItemRobot (free_item_keywords.robot) สืบทอด method ชื่อเดียวกัน
# มาจาก NewPriceRobot - ถ้า import ทั้ง 2 ไฟล์นี้พร้อมกันในไฟล์ทดสอบเดียว
# (เช่น promotion.robot ที่เลือกรัน New Price หรือ Free Item ด้วย Run
# Keyword If) เรียกแบบไม่ระบุชื่อเต็มจะเจอ "Multiple keywords found" ทันที
Configure New Price Coordinates
    NewPriceRobot.Set New Price Coordinate    barcode_input    ${BARCODE_INPUT_X}    ${BARCODE_INPUT_Y}
    NewPriceRobot.Set New Price Coordinate    member_button    ${MEMBER_BUTTON_X}    ${MEMBER_BUTTON_Y}
    NewPriceRobot.Set New Price Coordinate    member_barcode_input    ${MEMBER_BARCODE_INPUT_X}    ${MEMBER_BARCODE_INPUT_Y}
    NewPriceRobot.Set New Price Coordinate    member_welcome_confirm_button    ${MEMBER_WELCOME_CONFIRM_X}    ${MEMBER_WELCOME_CONFIRM_Y}
    NewPriceRobot.Set New Price Coordinate    member_welcome_header    ${MEMBER_WELCOME_HEADER_X}    ${MEMBER_WELCOME_HEADER_Y}
    NewPriceRobot.Set New Price Coordinate    receive_exact_button    ${RECEIVE_EXACT_BUTTON_X}    ${RECEIVE_EXACT_BUTTON_Y}
    NewPriceRobot.Set New Price Coordinate    popup_confirm_yes_button    ${POPUP_CONFIRM_YES_X}    ${POPUP_CONFIRM_YES_Y}
    NewPriceRobot.Set New Price Coordinate    sign_off_button    ${SIGN_OFF_BUTTON_X}    ${SIGN_OFF_BUTTON_Y}
    NewPriceRobot.Set New Price Coordinate    invalid_barcode_popup_point    ${INVALID_BARCODE_POPUP_X}    ${INVALID_BARCODE_POPUP_Y}
    NewPriceRobot.Set New Price Coordinate    mstamp_popup_check_point    ${MSTAMP_POPUP_CHECK_X}    ${MSTAMP_POPUP_CHECK_Y}
    NewPriceRobot.Set New Price Coordinate    mstamp_button    ${MSTAMP_BUTTON_X}    ${MSTAMP_BUTTON_Y}
    NewPriceRobot.Set New Price Price Point    ${PRICE_DISPLAY_X}    ${PRICE_DISPLAY_Y}
    NewPriceRobot.Set New Price Setting    step_delay_seconds    ${STEP_DELAY_SECONDS}
    NewPriceRobot.Set New Price Setting    db_price_check_wait_seconds    ${DB_PRICE_CHECK_WAIT_SECONDS}
    NewPriceRobot.Set New Price Setting    db_price_check_timeout_seconds    ${DB_PRICE_CHECK_TIMEOUT_SECONDS}
    NewPriceRobot.Set New Price Setting    lpe_check_timeout_seconds    ${LPE_CHECK_TIMEOUT_SECONDS}
    NewPriceRobot.Set New Price Setting    popup_timeout_seconds    ${POPUP_TIMEOUT_SECONDS}
    NewPriceRobot.Set New Price Setting    receive_exact_retry_count    ${RECEIVE_EXACT_RETRY_COUNT}

Run New Price Promotion Test
    Configure New Price Coordinates
    ${log_path}=    NewPriceRobot.Run New Price Test Suite
    NewPriceRobot.Sign Off
    Should Not Be Empty    ${log_path}
    Log    บันทึกผลการทดสอบ New Price ที่: ${log_path}

Sign Off Only
    [Documentation]    ใช้เวลา reward_type ใน config ไม่รู้จัก (ไม่ใช่ทั้ง
    ...    "New Price" และ "Free Item") - ไม่รันชุดทดสอบไหนเลย แค่ตั้งพิกัด
    ...    แล้วกด Sign Off ปิดจบให้ปลอดภัย (เรียกจาก tests/promotion.robot)
    Configure New Price Coordinates
    NewPriceRobot.Sign Off

# ----------------------------------------------------------------------
# Keyword ช่วย calibrate พิกัด
# เอาเมาส์ไปวางที่ปุ่ม/ช่องจริงบนหน้าจอ POS ก่อน แล้วรัน keyword ที่ตรงกัน
# ด้านล่าง (หรือใช้ show_cursor_position.bat ก็ได้) จะได้ค่า x,y มา
# เอาไปกรอกแทนที่ Variables ด้านบน
# ----------------------------------------------------------------------
Capture Barcode Input Coordinate
    ${x}    ${y}=    Capture Current Cursor
    Log    BARCODE_INPUT: x=${x}, y=${y}

Capture Member Button Coordinate
    ${x}    ${y}=    Capture Current Cursor
    Log    MEMBER_BUTTON (ปุ่ม "สมาชิก / ใช้ M-Stamp" บนหน้าชำระเงิน หลังกด Add): x=${x}, y=${y}

Capture Member Barcode Input Coordinate
    ${x}    ${y}=    Capture Current Cursor
    Log    MEMBER_BARCODE_INPUT: x=${x}, y=${y}

Capture Member Welcome Confirm Coordinate
    ${x}    ${y}=    Capture Current Cursor
    Log    MEMBER_WELCOME_CONFIRM: x=${x}, y=${y}

Capture Member Welcome Header Coordinate
    ${x}    ${y}=    Capture Current Cursor
    Log    MEMBER_WELCOME_HEADER (ข้อความ "ยินดีต้อนรับสมาชิก..." สีเขียวด้านบน): x=${x}, y=${y}

Capture Receive Exact Button Coordinate
    ${x}    ${y}=    Capture Current Cursor
    Log    RECEIVE_EXACT_BUTTON: x=${x}, y=${y}

Capture Popup Confirm Yes Coordinate
    ${x}    ${y}=    Capture Current Cursor
    Log    POPUP_CONFIRM_YES: x=${x}, y=${y}

Capture Price Display Point
    ${x}    ${y}=    Capture Current Cursor
    Log    PRICE_DISPLAY: x=${x}, y=${y}

Capture Sign Off Button Coordinate
    ${x}    ${y}=    Capture Current Cursor
    Log    SIGN_OFF_BUTTON (ปุ่ม "1. Sign Off" บนหน้าเมนูหลังกด Esc): x=${x}, y=${y}

Capture Invalid Barcode Popup Point
    ${x}    ${y}=    Capture Current Cursor
    Log    INVALID_BARCODE_POPUP (พื้นสีเหลืองของ popup "รหัสบาร์โค้ดไม่ถูกต้อง"): x=${x}, y=${y}

Capture M-Stamp Popup Check Point
    ${x}    ${y}=    Capture Current Cursor
    Log    MSTAMP_POPUP_CHECK (พื้นสีเหลืองของ popup "สอบถามลูกค้าว่าต้องการรับ M-Stamp หรือแสตมป์"): x=${x}, y=${y}

Capture M-Stamp Button Coordinate
    ${x}    ${y}=    Capture Current Cursor
    Log    MSTAMP_BUTTON (ปุ่ม "M-Stamp" บน popup ข้างต้น): x=${x}, y=${y}
