*** Settings ***
Documentation    Keywords สำหรับเชื่อมต่อ VNC และล็อกอินระบบ POS
Library          RPA.Windows
Library          Process
Library          ocr_keywords.py
Library          member_api_keywords.py
Library          window_keywords.py

*** Keywords ***
Open VNC And Connect
    [Documentation]    เปิด UltraVNC Viewer เชื่อมต่อไปยัง server และล็อกอินผ่าน VNC
    [Arguments]    ${vnc_path}    ${server_ip}    ${vnc_password}
    # ปิด vncviewer.exe ที่ค้างจากการรันครั้งก่อนก่อนเปิดใหม่ ป้องกัน Control Window
    # error "Found more than one window with executable 'vncviewer.exe'"
    Run Keyword And Ignore Error    Run Process    taskkill    /IM    vncviewer.exe    /F
    Sleep    1.5s
    Windows Run    ${vnc_path}
    Sleep    1.5s
    Control Window    executable:vncviewer.exe
    Send Keys    keys=${server_ip}
    Click    name:Connect
    Wait Until Keyword Succeeds    6x    2s    Control Window    regex:.*Authentication.*
    Send Keys    keys=${vnc_password}
    Click    name:Login
    Sleep    1.5s
    # จัดหน้าต่าง cmd (ที่รัน robot อยู่) กับหน้าต่าง VNC ให้อยู่คนละฝั่งของจอ กันทับกัน
    # มองไม่เห็นทั้งคู่ (เจอปัญหาจริงตอนรันผ่าน .bat) ย้ายตำแหน่งเฉยๆ ไม่ resize หน้าต่าง VNC
    # เพื่อไม่ให้กระทบพิกัดคลิกตายตัวที่ calibrate ไว้ (ดูรายละเอียดใน window_keywords.py)
    Arrange Windows Side By Side    vncviewer.exe

Login To POS
    [Documentation]    ล็อกอินเข้าระบบ POS ด้วยรหัสพนักงานและรหัสผ่าน
    [Arguments]    ${emp_code}    ${emp_password}
    Control Window    executable:vncviewer.exe
    Sleep    1.5s
    Send Keys    keys=${emp_code}
    Send Keys    keys={ENTER}
    Send Keys    keys=${emp_password}
    Send Keys    keys={ENTER}
    Sleep    5s
    Send Keys    keys={ENTER}
    Sleep    2.5s

Scan Product By Barcode
    [Documentation]    สแกน/กรอกบาร์โค้ดสินค้าและกด Enter เพื่อเพิ่มลงรายการขาย
    ...    ถ้าจำนวน (qty) มากกว่า 1 จะคีย์รูปแบบ qty*barcode เช่น 2*8853002318602
    [Arguments]    ${barcode}    ${qty}=1
    ${keys}=    Set Variable If    ${qty} > 1    ${qty}*${barcode}    ${barcode}
    Control Window    executable:vncviewer.exe
    Sleep    2s
    Send Keys    keys=${keys}
    Sleep    2.5s
    Send Keys    keys={ENTER}

Press Plus Key
    [Documentation]    กดปุ่มบวก (+) บนคีย์บอร์ด
    Control Window    executable:vncviewer.exe
    Sleep    3s
    # ต้องใช้ {Add} ไม่ใช่ {+} เพราะ POS รับเฉพาะปุ่ม + ฝั่ง Numpad จริง (VK_ADD)
    Send Keys    keys={Add}
    Sleep    2s

Get Amount Due From Screen
    [Documentation]    แคปหน้าจอหน้าชำระเงินแล้วอ่านตัวเลข "ยอดที่ต้องชำระ" ด้วย OCR
    ${window}=    Control Window    executable:vncviewer.exe
    ${image}=    Screenshot    executable:vncviewer.exe    ${OUTPUT_DIR}${/}payment_screen.png
    ${amount}=    Read Amount From Image    ${image}
    RETURN    ${amount}

Get Unit Price From Screen
    [Documentation]    แคปหน้าจอชำระเงินแล้วอ่าน "ยอดรวม" (ราคาเต็มก่อนหักส่วนลด) ด้วย OCR
    ...    แล้วหารด้วยจำนวนชิ้นเพื่อได้ราคาต่อชิ้น (ตารางรายการไม่แสดงแล้วหลังกด + จึงอ่าน
    ...    "ยอดรวม" แทนคอลัมน์ "ราคา/หน่วย")
    [Arguments]    ${trigger_value}
    ${window}=    Control Window    executable:vncviewer.exe
    ${image}=    Screenshot    executable:vncviewer.exe    ${OUTPUT_DIR}${/}unit_price_screen.png
    ${subtotal}=    Read Subtotal From Image    ${image}
    ${price}=    Evaluate    ${subtotal} / ${trigger_value}
    RETURN    ${price}

Click Exact Payment
    [Documentation]    คลิกปุ่ม "รับพอดี" (ชำระด้วยจำนวนเงินพอดี ไม่ต้องทอน)
    ...    offset คำนวณจากตำแหน่งปุ่มจริงบนกริด เทียบกับจุดกึ่งกลางหน้าต่าง (ภาพหน้าจอขนาด 1602x667)
    Control Window    executable:vncviewer.exe
    Click    executable:vncviewer.exe offset:-211,-25
    Sleep    1s

Click Member Button
    [Documentation]    คลิกปุ่ม "สมาชิก / ใช้ M-Stamp" (สำหรับโปรโมชั่นที่ต้องใช้บัตรสมาชิก)
    Control Window    executable:vncviewer.exe
    Click    executable:vncviewer.exe offset:-71,-192
    Sleep    1s

Click Member Confirm
    [Documentation]    คลิกปุ่ม "ยืนยัน" บนหน้าจอ "ยินดีต้อนรับสมาชิก" (หลังกรอกบาร์โค้ดสมาชิก)
    ...    หาตำแหน่งปุ่มด้วย OCR (อ่านคำว่า "ยืนยัน" บนภาพหน้าจอจริง) แทนการเดาพิกัดตายตัว
    ...    เพื่อให้คลิกถูกตำแหน่งเสมอไม่ว่าหน้าต่างจะขนาด/ตำแหน่งใดก็ตาม
    Control Window    executable:vncviewer.exe
    Sleep    2s
    ${image}=    Screenshot    executable:vncviewer.exe    ${OUTPUT_DIR}${/}member_confirm_screen.png
    # จำกัดพื้นที่สแกน OCR แค่มุมล่างขวาของฟอร์มสมาชิก (ที่ปุ่ม "ยืนยัน" อยู่จริง) ตัดทั้ง
    # ตารางรายการด้านบนและรูปโฆษณาฝั่งขวาออก เพราะเคยเจอเคสจริงที่สแกนพื้นที่กว้างเกินไป
    # แล้ว OCR มองข้ามปุ่มไปเลย (ยิ่งครอปแคบและตรงจุด ยิ่งอ่านเจอชัดเจน)
    ${offset}=    Find Text Offset From Center    ${image}    ยืนยัน
    ...    left_frac=0.30    top_frac=0.75    right_frac=0.55    bottom_frac=0.95
    Click    executable:vncviewer.exe offset:${offset}[0],${offset}[1]
    Sleep    1s

Apply Member Barcode
    [Documentation]    กดปุ่ม "สมาชิก / ใช้ M-Stamp" แล้วเรียก API ขอบาร์โค้ดสมาชิก
    ...    (AllMemberRequestBarcode) แล้วคีย์บาร์โค้ดที่ได้ลงในช่องของ POS ตามด้วย Enter
    ...    จากนั้นกดปุ่ม "ยืนยัน" บนหน้าจอสรุปข้อมูลสมาชิก/M-Stamp ที่เด้งขึ้นมา
    [Arguments]    ${api_url}    ${api_token}    ${identify_id}    ${identify_value}
    Click Member Button
    ${barcode}=    Get Member Barcode    ${api_url}    ${api_token}    ${identify_id}    ${identify_value}
    Control Window    executable:vncviewer.exe
    Sleep    3s
    Send Keys    keys=${barcode}
    Send Keys    keys={ENTER}
    Sleep    2s
    Click Member Confirm

Confirm Payment
    [Documentation]    ยืนยันกล่องข้อความ "ยืนยันรับชำระ" โดยเลือกปุ่ม "ใช่"
    ...    (ปุ่ม "ไม่ใช่" เป็น default โฟกัสอยู่ ต้องกด Left ย้ายไปปุ่ม "ใช่" ก่อนกด Enter)
    Control Window    executable:vncviewer.exe
    Sleep    1.5s
    # กด Enter เฉยๆ จะเท่ากับกด "ไม่ใช่" เพราะเป็นปุ่ม default ที่โฟกัสอยู่ ต้อง {LEFT} ย้ายโฟกัสไป "ใช่" ก่อน
    Send Keys    keys={LEFT}{ENTER}
    # รอให้ POS ประมวลผลรายการ (พิมพ์ใบเสร็จ/เคลียร์หน้าจอ/โฟกัสกลับช่องบาร์โค้ด) ก่อนขายรายการถัดไป
    Sleep    1.5s

Clear Stray Error Dialog
    [Documentation]    เช็คด้วย OCR ก่อนว่ามี dialog error "ไม่สามารถรับชำระ" ค้างอยู่จากรอบก่อนหน้าไหม
    ...    ถ้ามีจริงถึงจะกด ESC ปิด ถ้าไม่มี (เช่น อยู่หน้าขายของปกติ) จะไม่กด ESC เลย
    ...    เพื่อกัน ESC หลุดออกไปหน้าเมนูหลักโดยไม่ตั้งใจ
    Control Window    executable:vncviewer.exe
    ${image}=    Screenshot    executable:vncviewer.exe    ${OUTPUT_DIR}${/}error_dialog_check.png
    ${found}=    Screen Contains Text    ${image}    ไม่สามารถรับชำระ
    IF    ${found}
        Send Keys    keys={ESC}
        Sleep    1s
    END

Sell Product
    [Documentation]    ขายสินค้า: สแกนบาร์โค้ดแล้วกดปุ่มบวก (+) เพื่อเพิ่มลงรายการขาย
    [Arguments]    ${barcode}    ${qty}=1
    Clear Stray Error Dialog
    Scan Product By Barcode    ${barcode}    ${qty}
    Press Plus Key

Sell Items Until Threshold
    [Documentation]    ขาย "1 บิล" จากกลุ่มบาร์โค้ดทางเลือกของ promotion_code เดียวกัน โดยเริ่ม
    ...    สแกนจากตำแหน่ง start_index ในลิสต์ (ไม่ใช่เริ่มจากตัวแรกเสมอ — ใช้ต่อยอดจากบิลก่อนหน้าได้)
    ...    วนสแกนทีละตัว เช็คยอดรวมหลังสแกนแต่ละครั้ง (อ่านจากกล่อง "ยอดที่ต้องชำระ" มุมขวาบน
    ...    ซึ่งขึ้นตั้งแต่หน้าสแกนสินค้าแล้ว ไม่ต้องกด + ก่อน) จนกว่ายอดจะถึง trigger_value
    ...    ถ้าสแกนจนหมดบาร์โค้ดในกลุ่มแล้วยังไม่ถึง จะสแกนบาร์โค้ดตัวสุดท้ายซ้ำไปเรื่อยๆ จนกว่าจะถึงเกณฑ์
    ...    แล้วกดปุ่มบวก (+) ครั้งเดียวตอนจบบิลนี้เพื่อไปหน้าชำระเงิน
    ...    คืนค่า index ตัวถัดไปที่ยังไม่ได้สแกน (ไว้ให้บิลถัดไปเริ่มต่อจากตรงนี้)
    [Arguments]    ${barcodes}    ${trigger_value}    ${start_index}=0
    Clear Stray Error Dialog
    ${count}=    Get Length    ${barcodes}
    ${index}=    Set Variable    ${start_index}
    ${total}=    Set Variable    ${0}
    WHILE    ${total} < ${trigger_value}
        IF    ${index} < ${count}
            ${barcode}=    Set Variable    ${barcodes}[${index}]
        ELSE
            ${barcode}=    Set Variable    ${barcodes}[-1]
        END
        Scan Product By Barcode    ${barcode}
        ${total}=    Get Amount Due From Screen
        Log To Console    สแกน ${barcode} แล้ว ยอดรวมตอนนี้ ${total} บาท (เกณฑ์ ${trigger_value})
        ${index}=    Evaluate    ${index} + 1
    END
    Press Plus Key
    RETURN    ${index}

Sell Until Payable Meets Threshold
    [Documentation]    ขาย "1 บิล" เหมือน Sell Items Until Threshold แต่เพิ่มการเช็คซ้ำหลังกด +
    ...    เพราะพบเคสจริงที่ตอนสแกน (ก่อนกด +) ยอดดูเหมือนถึงเกณฑ์แล้ว (เช่น 424 >= 399) แต่พอกด +
    ...    ไปหน้าชำระเงินแล้ว มีส่วนลดพิเศษเข้ามาเพิ่ม (เช่น -45) ทำให้ "ยอดที่ต้องชำระ" จริงเหลือ
    ...    ต่ำกว่าเกณฑ์ (379 < 399) ถ้าเจอแบบนี้จะกด ESC ย้อนกลับไปหน้าสแกนสินค้า (ตะกร้าเดิมไม่หาย)
    ...    แล้วขายเพิ่มต่อจนกว่ายอดที่ต้องชำระหลังกด + จะถึงเกณฑ์จริงๆ คืนค่า index ตัวถัดไปที่ยังไม่ได้สแกน
    [Arguments]    ${barcodes}    ${trigger_value}    ${start_index}=0
    ${index}=    Set Variable    ${start_index}
    ${actual}=    Set Variable    ${0}
    WHILE    ${actual} < ${trigger_value}
        ${index}=    Sell Items Until Threshold    ${barcodes}    ${trigger_value}    ${index}
        ${actual}=    Get Amount Due From Screen
        IF    ${actual} < ${trigger_value}
            Log To Console
            ...    หลังกด + ยอดที่ต้องชำระ ${actual} ยังไม่ถึงเกณฑ์ ${trigger_value} (มีส่วนลดเพิ่มเข้ามา) วนกลับไปขายต่อ
            Control Window    executable:vncviewer.exe
            Send Keys    keys={ESC}
            Sleep    1s
        END
    END
    RETURN    ${index}

Pay For Product
    [Documentation]    กดสมาชิก+ยืนยัน (ถ้าโปรโมชั่นนี้ต้องใช้บัตรสมาชิก) แล้วเช็คยอดที่ต้องชำระบนหน้าจอ
    ...    ให้ตรงกับที่คาดไว้ แล้วกด "รับพอดี" และยืนยันการชำระ
    ...    (member_segmentation = "All Members (card required)" ต้องกดสมาชิก+ยืนยันก่อนเช็คยอดเสมอ
    ...    เพราะราคาโปรโมชั่นจะยังไม่ขึ้นจนกว่าจะยืนยันสมาชิกแล้ว)
    [Arguments]    ${barcode}    ${expected_amount}    ${member_segmentation}
    ...    ${member_api_url}=${EMPTY}    ${member_api_token}=${EMPTY}
    ...    ${member_identify_id}=${EMPTY}    ${member_identify_value}=${EMPTY}
    IF    '${member_segmentation}' == 'All Members (card required)'
        Apply Member Barcode    ${member_api_url}    ${member_api_token}    ${member_identify_id}    ${member_identify_value}
    ELSE IF    '${member_segmentation}' != 'Apply Promotion to All Customers (no card required)'
        # กันเงื่อนไข member_segmentation ที่ไม่รู้จัก (สะกดต่าง/ค่าใหม่) ไม่ให้ข้ามเงียบๆ
        Fail    ไม่รู้จัก member_segmentation: ${member_segmentation}
    END
    ${actual}=    Get Amount Due From Screen
    Should Be Equal As Numbers
    ...    ${actual}    ${expected_amount}
    ...    msg=บาร์โค้ด ${barcode}: ยอดที่ต้องชำระ (${actual}) ไม่ตรงกับ reward_value (${expected_amount})
    Click Exact Payment
    Confirm Payment

Pay For Free Item
    [Documentation]    สำหรับโปรโมชั่น reward_type = "Free Item" (ซื้อครบแถมฟรี เช่น 1 แถม 1)
    ...    ไม่มี reward_value ตรงๆ เหมือน New Price ต้องคำนวณเอง:
    ...    expected_amount = (trigger_value - 1) × ราคาต่อชิ้น (อ่านจากคอลัมน์ "ราคา/หน่วย" บนหน้าจอ)
    ...    กดสมาชิก+ยืนยัน (ถ้าโปรโมชั่นนี้ต้องใช้บัตรสมาชิก) ก่อนเช็คราคาเสมอ เพราะราคาโปรโมชั่น
    ...    จะยังไม่ขึ้นจนกว่าจะยืนยันสมาชิกแล้ว จากนั้นกด "รับพอดี" และยืนยันการชำระ
    [Arguments]    ${barcode}    ${trigger_value}    ${member_segmentation}
    ...    ${member_api_url}=${EMPTY}    ${member_api_token}=${EMPTY}
    ...    ${member_identify_id}=${EMPTY}    ${member_identify_value}=${EMPTY}
    IF    '${member_segmentation}' == 'All Members (card required)'
        Apply Member Barcode    ${member_api_url}    ${member_api_token}    ${member_identify_id}    ${member_identify_value}
    ELSE IF    '${member_segmentation}' != 'Apply Promotion to All Customers (no card required)'
        # กันเงื่อนไข member_segmentation ที่ไม่รู้จัก (สะกดต่าง/ค่าใหม่) ไม่ให้ข้ามเงียบๆ
        Fail    ไม่รู้จัก member_segmentation: ${member_segmentation}
    END
    ${unit_price}=    Get Unit Price From Screen    ${trigger_value}
    ${expected_amount}=    Evaluate    (${trigger_value} - 1) * ${unit_price}
    ${actual}=    Get Amount Due From Screen
    Should Be Equal As Numbers
    ...    ${actual}    ${expected_amount}
    ...    msg=บาร์โค้ด ${barcode}: ยอดที่ต้องชำระ (${actual}) ไม่ตรงกับที่คำนวณได้ (${expected_amount} = (${trigger_value}-1)×${unit_price})
    Click Exact Payment
    Confirm Payment

Pay For Item Spend
    [Documentation]    สำหรับโปรโมชั่น reward_type = "Earn Points/Credits/Visits" ที่ trigger_type = "ItemSpend"
    ...    ที่นี่ trigger_value ไม่ใช่จำนวนชิ้น แต่เป็น "ยอดเงินขั้นต่ำ (บาท)" ที่ต้องซื้อสินค้านี้ให้ถึง
    ...    เช่น trigger_value=399 ต้องซื้อสินค้าจนราคารวมของชิ้นนี้ >= 399 บาท ถึงจะเข้าเงื่อนไข
    ...    (ไม่ใช่การเทียบเท่ากันตรงๆ เหมือน New Price/Free Item)
    ...    กดสมาชิก+ยืนยัน (ถ้าโปรโมชั่นนี้ต้องใช้บัตรสมาชิก) ก่อนเช็คราคาเสมอ จากนั้นกด "รับพอดี" และยืนยันการชำระ
    [Arguments]    ${barcode}    ${trigger_value}    ${member_segmentation}
    ...    ${member_api_url}=${EMPTY}    ${member_api_token}=${EMPTY}
    ...    ${member_identify_id}=${EMPTY}    ${member_identify_value}=${EMPTY}
    IF    '${member_segmentation}' == 'All Members (card required)'
        Apply Member Barcode    ${member_api_url}    ${member_api_token}    ${member_identify_id}    ${member_identify_value}
    ELSE IF    '${member_segmentation}' != 'Apply Promotion to All Customers (no card required)'
        # กันเงื่อนไข member_segmentation ที่ไม่รู้จัก (สะกดต่าง/ค่าใหม่) ไม่ให้ข้ามเงียบๆ
        Fail    ไม่รู้จัก member_segmentation: ${member_segmentation}
    END
    ${actual}=    Get Amount Due From Screen
    Should Be True
    ...    ${actual} >= ${trigger_value}
    ...    msg=บาร์โค้ด ${barcode}: ยอดที่ต้องชำระ (${actual}) ไม่ถึงเกณฑ์ trigger_value (${trigger_value})
    Click Exact Payment
    Confirm Payment

Sell One From Each Bucket
    [Documentation]    สแกนสินค้า 1 ชิ้นจากแต่ละ bucket (ตามตำแหน่ง index ที่ระบุ วนซ้ำเองถ้า index
    ...    เกินความยาวของ bucket นั้นๆ ด้วย modulo) แล้วกดปุ่มบวก (+) ครั้งเดียวตอนจบ
    ...    ใช้กับโปรที่ต้องซื้อสินค้า "คู่กัน" จากหลาย bucket ในบิลเดียว (เช่น bucketid=1 ถั่ว
    ...    + bucketid=2 นม) ไม่ใช่เลือกตัวใดตัวหนึ่งแบบ Sell Items Until Threshold
    ...    log entity_code/entity_name ของแต่ละชิ้นที่ขายในบิลนี้ไว้ด้วย เพื่อดูว่าบิลนี้ขายสินค้าอะไรบ้าง
    [Arguments]    ${buckets}    ${index}    ${qty}=1
    Clear Stray Error Dialog
    FOR    ${bucket}    IN    @{buckets}
        ${bucket_len}=    Get Length    ${bucket}
        ${pos}=    Evaluate    ${index} % ${bucket_len}
        ${item}=    Set Variable    ${bucket}[${pos}]
        Log To Console    ขาย ${item}[entity_code],${item}[entity_name]
        Scan Product By Barcode    ${item}[barcode]    ${qty}
    END
    Press Plus Key

Pay Without Amount Check
    [Documentation]    กดสมาชิก+ยืนยัน (ถ้าโปรโมชั่นนี้ต้องใช้บัตรสมาชิก) แล้วกด "รับพอดี" และยืนยัน
    ...    การชำระ โดยไม่เช็คยอดที่ต้องชำระเลย (ใช้กับโปรที่ reward เป็นแต้ม/สแตมป์ ไม่ใช่ส่วนลดราคา
    ...    จึงไม่มีค่าที่คาดไว้ให้เทียบ)
    [Arguments]    ${member_segmentation}
    ...    ${member_api_url}=${EMPTY}    ${member_api_token}=${EMPTY}
    ...    ${member_identify_id}=${EMPTY}    ${member_identify_value}=${EMPTY}
    IF    '${member_segmentation}' == 'All Members (card required)'
        Apply Member Barcode    ${member_api_url}    ${member_api_token}    ${member_identify_id}    ${member_identify_value}
    ELSE IF    '${member_segmentation}' != 'Apply Promotion to All Customers (no card required)'
        # กันเงื่อนไข member_segmentation ที่ไม่รู้จัก (สะกดต่าง/ค่าใหม่) ไม่ให้ข้ามเงียบๆ
        Fail    ไม่รู้จัก member_segmentation: ${member_segmentation}
    END
    Click Exact Payment
    Confirm Payment
