*** Settings ***
Documentation     ทดสอบขายสินค้าตามโปรโมชั่น Earn Points/Credits/Visits (trigger_type = ItemSpend/Quantity) จากฐานข้อมูล ประมวลผลตามลำดับที่พบในฐานข้อมูลจริง
Resource          ../resources/pos_keywords.robot
Library           ../resources/db_keywords.py
Variables         ../data/pos_data.json
Variables         ../data/member_api_data.json
Suite Teardown    Close Current Window

*** Test Cases ***
Open VNC
    [Documentation]    เปิดโปรแกรม VNC
    Open VNC And Connect    ${VNC}    ${SERVER_IP}    ${VNC_PASSWORD}

login Pos
    [Documentation]    ล็อกอินเข้าระบบ POS ด้วยรหัสพนักงานและรหัสผ่าน
    Login To POS    ${EMP_CODE}    ${EMP_PASSWORD}

Earn Points
    [Documentation]    ดึงรายการโปรโมชั่น Earn Points/Credits/Visits ในช่วง BATCH_START/BATCH_END จาก
    ...    ฐานข้อมูล "โดยไม่กรอง trigger_type" (เพื่อให้ตำแหน่ง row นับรวมทุก trigger_type ตัวเดียวกับที่
    ...    เห็นตอนดูข้อมูลทั้งหมด ไม่ใช่นับแยกเฉพาะกลุ่ม) จัดกลุ่มตาม promotion_code โดยรักษาลำดับที่
    ...    เจอในฐานข้อมูลไว้ (Group Rows By Promotion) แล้ววนทีละกลุ่ม "ตามลำดับที่เจอจริง" (เจอ
    ...    Quantity ก่อนก็ทำ Quantity ก่อน เจอ ItemSpend ก็ทำ ItemSpend ตามนั้น ไม่ใช่แยกทำ ItemSpend
    ...    ทั้งหมดก่อนแล้วค่อยทำ Quantity ทีหลัง) โดยเช็ค trigger_type ของแต่ละกลุ่มด้วย IF:
    ...    - Quantity: ต้องซื้อสินค้า "คู่กัน" จากหลาย bucket ในบิลเดียว (เช่น bucketid=1 ถั่ว
    ...      + bucketid=2 นม) ขายเป็นหลายบิล บิลละ 1 ชิ้นจากแต่ละ bucket (วนซ้ำ bucket ที่สั้นกว่า
    ...      ด้วย modulo) จนกว่าทุก bucket จะถูกใช้ครบทุกตัวอย่างน้อยคนละ 1 ครั้ง เช็คแค่
    ...      member_segmentation ไม่เช็คราคา (reward เป็นแต้ม/สแตมป์ ไม่ใช่ส่วนลดราคา)
    ...    - ItemSpend: trigger_value เป็นยอดเงินขั้นต่ำ (บาท) ไม่ใช่จำนวนชิ้น ขายเป็น "หลายบิล"
    ...      ต่อเนื่องกัน บิลแรกขายบาร์โค้ดตัวแรกๆ จนครบเกณฑ์ (Sell Until Payable Meets Threshold)
    ...      แล้วจ่ายจบบิล (Pay For Item Spend) บิลถัดไปขายต่อจากบาร์โค้ดตัวที่ค้างไว้ วนแบบนี้จนกว่า
    ...      จะขายครบทุกบาร์โค้ดในกลุ่ม (ถ้าบิลสุดท้ายบาร์โค้ดที่เหลือไม่พอครบเกณฑ์ จะขายบาร์โค้ดตัว
    ...      สุดท้ายซ้ำ)
    ${rows}=    Get Promotion Rows    ${CURDIR}/../data/${DB_FILE}    Earn Points/Credits/Visits    ${ACTIVE_FROM}    ${SHEET}
    ...    start_row=${BATCH_START}    end_row=${BATCH_END}
    ${groups}=    Group Rows By Promotion    ${rows}
    FOR    ${group}    IN    @{groups}
        IF    '${group}[trigger_type]' == 'Quantity'
            ${bucket_count}=    Get Length    ${group}[buckets]
            ${max_len}=    Set Variable    ${0}
            FOR    ${bucket}    IN    @{group}[buckets]
                ${bucket_len}=    Get Length    ${bucket}
                IF    ${bucket_len} > ${max_len}
                    ${max_len}=    Set Variable    ${bucket_len}
                END
            END
            Log To Console
            ...    ${group}[promotion_code],${group}[promotion_name] (Quantity) มี ${bucket_count} bucket ต้องขายทั้งหมด ${max_len} บิล

            FOR    ${round}    IN RANGE    ${max_len}
                # ขายสินค้า 1 บิล: 1 ชิ้นจากแต่ละ bucket (ตำแหน่งที่ ${round} วนซ้ำเองถ้าหมด bucket)
                Sell One From Each Bucket    ${group}[buckets]    ${round}    ${group}[trigger_value]

                # เช็ค member_segmentation แล้วจ่ายให้จบบิล (ไม่เช็คราคา)
                Pay Without Amount Check
                ...    ${group}[member_segmentation]
                ...    ${MEMBER_API_URL}    ${MEMBER_API_TOKEN}    ${MEMBER_IDENTIFY_ID}    ${MEMBER_IDENTIFY_VALUE}
            END
        ELSE IF    '${group}[trigger_type]' == 'ItemSpend'
            ${barcode_count}=    Get Length    ${group}[barcodes]
            Log To Console
            ...    ${group}[promotion_code],${group}[promotion_name] (ItemSpend) มีบาร์โค้ดทางเลือก ${barcode_count} ตัว ยอดขั้นต่ำ ${group}[trigger_value] บาท

            ${index}=    Set Variable    ${0}
            WHILE    ${index} < ${barcode_count}
                # ขายสินค้า 1 บิล เริ่มจากบาร์โค้ดตัวที่ ${index} จนกว่ายอดที่ต้องชำระ "หลังกด +"
                # (ซึ่งสะท้อนส่วนลดพิเศษที่อาจเพิ่มเข้ามาจริงๆ) จะถึงเกณฑ์ ไม่ใช่แค่ยอดตอนสแกน
                ${index}=    Sell Until Payable Meets Threshold    ${group}[barcodes]    ${group}[trigger_value]    ${index}

                # เช็คว่ายอดที่ต้องชำระถึงเกณฑ์ trigger_value (บาท) หรือไม่ แล้วชำระเงินปิดบิลนี้
                Pay For Item Spend
                ...    ${group}[promotion_code]    ${group}[trigger_value]    ${group}[member_segmentation]
                ...    ${MEMBER_API_URL}    ${MEMBER_API_TOKEN}    ${MEMBER_IDENTIFY_ID}    ${MEMBER_IDENTIFY_VALUE}
            END
        ELSE
            # กันเงื่อนไข trigger_type ที่ไม่รู้จัก (สะกดต่าง/ค่าใหม่) ไม่ให้ข้ามเงียบๆ
            Fail    ไม่รู้จัก trigger_type: ${group}[trigger_type] (promotion_code ${group}[promotion_code])
        END
    END
