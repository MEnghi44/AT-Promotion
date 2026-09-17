*** Settings ***
Documentation     login POS แล้วรันชุดทดสอบตาม reward_type ใน
...               login_credentials.json (new_price.reward_type):
...               - "Free Item"   -> รัน Free Item test suite
...               - "New Price"   -> รัน New Price test suite
...               - "Amount Off"  -> รัน Amount Off test suite
...               - ค่าอื่น/ไม่รู้จัก -> ไม่รันชุดทดสอบไหนเลย (กันพลาดยิงผิด
...                 suite) แค่ตั้งพิกัดแล้วกด Sign Off ปิดจบให้ปลอดภัย
...               Robot Framework 3.1.2 ไม่มี IF/ELSE block ใช้ Run Keyword
...               If จาก BuiltIn แทน
Resource          ../resources/login_keywords.robot
Resource          ../resources/new_price_keywords.robot
Resource          ../resources/free_item_keywords.robot
Resource          ../resources/amount_off_keywords.robot

*** Test Cases ***
Promotion Test
    Check Store Code Before Login
    Login With Credentials From Json
    ${reward_type}=    NewPriceRobot.Get New Price Setting    reward_type
    Run Keyword If    '${reward_type}' == 'Free Item'
    ...    Run Free Item Promotion Test
    ...    ELSE IF    '${reward_type}' == 'New Price'
    ...    Run New Price Promotion Test
    ...    ELSE IF    '${reward_type}' == 'Amount Off'
    ...    Run Amount Off Promotion Test
    ...    ELSE
    ...    Sign Off Only
