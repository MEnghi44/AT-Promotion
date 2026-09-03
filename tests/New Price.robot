*** Settings ***
Documentation     ทดสอบขายสินค้าตามโปรโมชั่น New Price จากฐานข้อมูล
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

New Price
    [Documentation]    ดึงรายการโปรโมชั่น New Price จากฐานข้อมูล แล้ววนขายทีละรายการต่อเนื่องกันโดยไม่ login ใหม่
    ...    แต่ละรายการแยกเป็น 2 ขั้นตอนชัดเจน: ขายสินค้า (Sell Product) แล้วชำระยอดและชำระเงิน (Pay For Product)
    ${rows}=    Get Promotion Rows    ${CURDIR}/../data/${DB_FILE}    New Price    ${ACTIVE_FROM}    ${SHEET}    ${BATCH_START}    ${BATCH_END}
    FOR    ${row}    IN    @{rows}
        Log To Console
        ...    ${row}[promotion_code],${row}[promotion_name],${row}[entity_code],${row}[entity_name],${row}[barcode] จำนวน ${row}[trigger_value]

        # ขายสินค้า
        Sell Product    ${row}[barcode]    ${row}[trigger_value]

        # ชำระยอดและชำระเงิน (รวมกดสมาชิก+ยืนยันไว้ในนี้ ถ้าโปรโมชั่นนี้ต้องใช้บัตรสมาชิก)
        Pay For Product
        ...    ${row}[barcode]    ${row}[reward_value]    ${row}[member_segmentation]
        ...    ${MEMBER_API_URL}    ${MEMBER_API_TOKEN}    ${MEMBER_IDENTIFY_ID}    ${MEMBER_IDENTIFY_VALUE}
    END
