from datetime import datetime

import requests
from robot.api.deco import keyword, library


@library
class member_api_keywords:

    @keyword
    def get_member_barcode(self, url, token, identify_id, identify_value):
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        }
        body = {
            # API ต้องการ "/" คั่นวันที่ (เช่น 2025/01/16 16:18:50) ใช้ "-" แล้ว API จะตอบ
            # returnCode 71001 "Invalid data" ทันที
            "sysDatetime": datetime.now().strftime("%Y/%m/%d %H:%M:%S"),
            "identifyId": identify_id,
            "identifyValue": identify_value,
        }
        response = requests.post(url, json=body, headers=headers, timeout=15)
        response.raise_for_status()
        data = response.json()
        if data.get("returnCode") != "00000":
            raise ValueError(f"RequestBarcode failed: {data}")
        return data["barcodeId"]
