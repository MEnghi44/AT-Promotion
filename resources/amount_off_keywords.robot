*** Settings ***
Documentation     Keyword สำหรับ flow ทดสอบโปรโมชัน "Amount Off" (ซื้อสินค้า
...               bucketid=1 ให้ครบยอดสะสมตาม trigger_value เพื่อปลดล็อก
...               สินค้า bucketid=2 ราคาพิเศษ) ลอจิกหลัก (สแกนสะสมยอด,
...               ประมาณราคาจาก MS_PRICE_SALE, เช็คส่วนลดจริงด้วย OCR ที่
...               หน้าชำระเงิน, Esc กลับไปสแกนเพิ่ม, ปิดบิล) อยู่ใน
...               AmountOffRobot.py (subclass ของ NewPriceRobot + PriceOcr)
...               พิกัดหน้าจอเก็บไว้เป็น Variables ในไฟล์นี้แยกจาก
...               new_price_keywords.robot/free_item_keywords.robot - ถ้า
...               calibrate พิกัดที่ใช้ร่วมกัน (barcode_input, popup ต่างๆ
...               ฯลฯ) ใหม่ที่นั่น ต้องมาอัปเดตที่นี่ด้วย (เป็นเครื่อง POS
...               จอเดียวกัน)
...
...               จุดที่เพิ่มมาเฉพาะ Amount Off (ยังไม่ calibrate ค่าจริง
...               ตั้งเป็น 0/0 ไว้ก่อน):
...               - go_to_payment_button: ปุ่ม/ทางไปหน้า B (ชำระเงิน) จากหน้า A
...               - amount_due_field / amount_due_field_size: กรอบสี่เหลี่ยม
...                 ครอบตัวเลข "ยอดที่ต้องชำระ" บนหน้า B ให้ OCR อ่าน
...               - ocr_background: จุดพื้นหลังในกรอบนั้น (ไม่มีตัวเลขทับ)
...               - price digit template ของ 0-9 และ '.' (เก็บลง
...                 data/price_ocr_templates.json ผ่าน Capture Price Digit
...                 Template ด้านล่าง ต้องทำให้ครบก่อนใช้งานจริง)
Library           ../libraries/CoordinateRobot.py    ../data/login_credentials.json
Library           ../libraries/AmountOffRobot.py    ../data/login_credentials.json

*** Variables ***
# ค่าที่ใช้ร่วมกับ New Price/Free Item (copy มาจาก new_price_keywords.robot)
${BARCODE_INPUT_X}                  17
${BARCODE_INPUT_Y}                  58
${MEMBER_BUTTON_X}                  725
${MEMBER_BUTTON_Y}                  82
${MEMBER_BARCODE_INPUT_X}           50
${MEMBER_BARCODE_INPUT_Y}           150
${MEMBER_WELCOME_CONFIRM_X}         720
${MEMBER_WELCOME_CONFIRM_Y}         515
${MEMBER_WELCOME_HEADER_X}          15
${MEMBER_WELCOME_HEADER_Y}          15
${RECEIVE_EXACT_BUTTON_X}           575
${RECEIVE_EXACT_BUTTON_Y}           240
${POPUP_CONFIRM_YES_X}              320
${POPUP_CONFIRM_YES_Y}              350
${SIGN_OFF_BUTTON_X}                 400
${SIGN_OFF_BUTTON_Y}                 186
${INVALID_BARCODE_POPUP_X}          220
${INVALID_BARCODE_POPUP_Y}          240
${MSTAMP_POPUP_CHECK_X}             220
${MSTAMP_POPUP_CHECK_Y}             240
${MSTAMP_BUTTON_X}                  320
${MSTAMP_BUTTON_Y}                  350

# เวลาหน่วง/timeout ต่างๆ (เหมือน new_price_keywords.robot)
${STEP_DELAY_SECONDS}               4
${DB_PRICE_CHECK_WAIT_SECONDS}      10
${DB_PRICE_CHECK_TIMEOUT_SECONDS}   30
${LPE_CHECK_TIMEOUT_SECONDS}        30
${POPUP_TIMEOUT_SECONDS}            30
${RECEIVE_EXACT_RETRY_COUNT}        1

# ----------------------------------------------------------------------
# ค่าเฉพาะ Amount Off - ยังไม่ calibrate (0/0) ต้องตั้งค่าจริงก่อนใช้งาน
# ----------------------------------------------------------------------

# ปุ่ม/ทางไปหน้า "ชำระเงิน" (หน้า B) จากหน้า "เพิ่มสินค้า" (หน้า A)
${GO_TO_PAYMENT_BUTTON_X}           0
${GO_TO_PAYMENT_BUTTON_Y}           0

# มุมบนซ้ายของกรอบสี่เหลี่ยมที่ครอบตัวเลข "ยอดที่ต้องชำระ" บนหน้า B ให้กว้าง
# พอครอบตัวเลขที่เป็นไปได้ทุกความยาว (เผื่อไว้ เกินได้ไม่เป็นไร OCR จะหา
# เฉพาะคอลัมน์ที่มีตัวเลขจริงเอง)
${AMOUNT_DUE_FIELD_X}                0
${AMOUNT_DUE_FIELD_Y}                0
${AMOUNT_DUE_FIELD_WIDTH}            0
${AMOUNT_DUE_FIELD_HEIGHT}           0

# จุดพื้นหลังว่างๆในกรอบข้างบน (ไม่มีตัวเลขทับ) ใช้แยกตัวเลข(foreground)
# ออกจากพื้น(background) ตอนอ่านค่าจริง
${OCR_BACKGROUND_X}                  0
${OCR_BACKGROUND_Y}                  0

# จำนวนครั้งสูงสุดที่จะสแกนสินค้า bucketid=1 เพิ่ม (รวมทุกรอบ Esc กลับไป
# สแกนเพิ่ม) ก่อนจะถือว่าผิดปกติแล้ว fail แถวนั้น (กันวนลูปไม่จบถ้าราคาจริง
# ผิดจาก MS_PRICE_SALE มากๆ หรือ OCR อ่านค่าผิดซ้ำๆ)
${AMOUNT_OFF_MAX_SCAN_ATTEMPTS}      30

*** Keywords ***
Configure Amount Off Coordinates
    AmountOffRobot.Set New Price Coordinate    barcode_input    ${BARCODE_INPUT_X}    ${BARCODE_INPUT_Y}
    AmountOffRobot.Set New Price Coordinate    member_button    ${MEMBER_BUTTON_X}    ${MEMBER_BUTTON_Y}
    AmountOffRobot.Set New Price Coordinate    member_barcode_input    ${MEMBER_BARCODE_INPUT_X}    ${MEMBER_BARCODE_INPUT_Y}
    AmountOffRobot.Set New Price Coordinate    member_welcome_confirm_button    ${MEMBER_WELCOME_CONFIRM_X}    ${MEMBER_WELCOME_CONFIRM_Y}
    AmountOffRobot.Set New Price Coordinate    member_welcome_header    ${MEMBER_WELCOME_HEADER_X}    ${MEMBER_WELCOME_HEADER_Y}
    AmountOffRobot.Set New Price Coordinate    receive_exact_button    ${RECEIVE_EXACT_BUTTON_X}    ${RECEIVE_EXACT_BUTTON_Y}
    AmountOffRobot.Set New Price Coordinate    popup_confirm_yes_button    ${POPUP_CONFIRM_YES_X}    ${POPUP_CONFIRM_YES_Y}
    AmountOffRobot.Set New Price Coordinate    sign_off_button    ${SIGN_OFF_BUTTON_X}    ${SIGN_OFF_BUTTON_Y}
    AmountOffRobot.Set New Price Coordinate    invalid_barcode_popup_point    ${INVALID_BARCODE_POPUP_X}    ${INVALID_BARCODE_POPUP_Y}
    AmountOffRobot.Set New Price Coordinate    mstamp_popup_check_point    ${MSTAMP_POPUP_CHECK_X}    ${MSTAMP_POPUP_CHECK_Y}
    AmountOffRobot.Set New Price Coordinate    mstamp_button    ${MSTAMP_BUTTON_X}    ${MSTAMP_BUTTON_Y}
    AmountOffRobot.Set New Price Coordinate    go_to_payment_button    ${GO_TO_PAYMENT_BUTTON_X}    ${GO_TO_PAYMENT_BUTTON_Y}
    AmountOffRobot.Set New Price Coordinate    amount_due_field    ${AMOUNT_DUE_FIELD_X}    ${AMOUNT_DUE_FIELD_Y}
    AmountOffRobot.Set New Price Coordinate    amount_due_field_size    ${AMOUNT_DUE_FIELD_WIDTH}    ${AMOUNT_DUE_FIELD_HEIGHT}
    AmountOffRobot.Set Price Ocr Background    ${OCR_BACKGROUND_X}    ${OCR_BACKGROUND_Y}
    AmountOffRobot.Set New Price Setting    step_delay_seconds    ${STEP_DELAY_SECONDS}
    AmountOffRobot.Set New Price Setting    db_price_check_wait_seconds    ${DB_PRICE_CHECK_WAIT_SECONDS}
    AmountOffRobot.Set New Price Setting    db_price_check_timeout_seconds    ${DB_PRICE_CHECK_TIMEOUT_SECONDS}
    AmountOffRobot.Set New Price Setting    lpe_check_timeout_seconds    ${LPE_CHECK_TIMEOUT_SECONDS}
    AmountOffRobot.Set New Price Setting    popup_timeout_seconds    ${POPUP_TIMEOUT_SECONDS}
    AmountOffRobot.Set New Price Setting    receive_exact_retry_count    ${RECEIVE_EXACT_RETRY_COUNT}
    AmountOffRobot.Set New Price Setting    amount_off_max_scan_attempts    ${AMOUNT_OFF_MAX_SCAN_ATTEMPTS}

Run Amount Off Promotion Test
    Configure Amount Off Coordinates
    ${log_path}=    AmountOffRobot.Run Amount Off Test Suite
    AmountOffRobot.Sign Off
    Should Not Be Empty    ${log_path}
    Log    บันทึกผลการทดสอบ Amount Off ที่: ${log_path}

# ----------------------------------------------------------------------
# Keyword ช่วย calibrate พิกัด/OCR
# เอาเมาส์ไปวางที่ปุ่ม/ช่องจริงบนหน้าจอ POS ก่อน แล้วรัน keyword ที่ตรงกัน
# ด้านล่าง จะได้ค่า x,y มาเอาไปกรอกแทนที่ Variables ด้านบน
# ----------------------------------------------------------------------
Capture Go To Payment Button Coordinate
    ${x}    ${y}=    Capture Current Cursor
    Log    GO_TO_PAYMENT_BUTTON: x=${x}, y=${y}

Capture Amount Due Field Point
    ${x}    ${y}=    Capture Current Cursor
    Log    AMOUNT_DUE_FIELD (มุมบนซ้ายของกรอบ "ยอดที่ต้องชำระ" บนหน้า B): x=${x}, y=${y}

Capture OCR Background Point
    ${x}    ${y}=    Capture Current Cursor
    Log    OCR_BACKGROUND (จุดพื้นหลังว่างๆในกรอบ amount_due_field): x=${x}, y=${y}

Capture Price Digit Template
    [Documentation]    เอาเมาส์ไปวางที่มุมบนซ้ายของตัวอักษร (digit) ตัวเดียว
    ...    บนหน้าจอจริงก่อน แล้วเรียก keyword นี้พร้อมระบุ digit ("0".."9"
    ...    หรือ ".") และ width/height (พิกเซล) ที่ครอบตัวอักษรนั้นพอดี -
    ...    เรียกทีละตัวให้ครบก่อนใช้งานจริง (บันทึกลง
    ...    data/price_ocr_templates.json ทันที ใช้ข้ามรอบรันได้)
    [Arguments]    ${digit}    ${width}    ${height}
    ${x}    ${y}=    Capture Current Cursor
    AmountOffRobot.Capture Price Digit Template    ${digit}    ${x}    ${y}    ${width}    ${height}
    Log    Captured OCR template for digit "${digit}" at x=${x}, y=${y}, size=${width}x${height}
