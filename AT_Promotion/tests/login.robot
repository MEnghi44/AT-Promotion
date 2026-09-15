*** Settings ***
Documentation     POS login test, plus the "New Price" promotion test which
...               reuses the same login keywords.
Resource          ../resources/login_keywords.robot
Resource          ../resources/new_price_keywords.robot

*** Test Cases ***
Promotion Test
    Check Store Code Before Login
    Login With Credentials From Json
    Run New Price Promotion Test
