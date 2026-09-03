import os
import re

import pytesseract
from PIL import Image
from robot.api.deco import keyword, library

_RESOURCES_DIR = os.path.dirname(os.path.abspath(__file__))
_DEFAULT_TESSERACT_PATH = os.path.join(_RESOURCES_DIR, "..", "tools", "Tesseract-OCR", "tesseract.exe")
pytesseract.pytesseract.tesseract_cmd = _DEFAULT_TESSERACT_PATH


def _fix_sara_am(text):
    # Tesseract บางครั้งอ่านสระ "ำ" (U+0E33 ตัวเดียว) เป็นรูปแยก "ํ" + "า" (U+0E4D + U+0E32)
    # ซึ่งมองด้วยตาเหมือนกันแต่เทียบสตริงตรงๆ ไม่ตรง (ไม่ใช่ Unicode canonically equivalent
    # จึง NFC normalize ก็ไม่ช่วย) ต้องแทนที่ด้วยมือก่อนเทียบ/ค้นหาข้อความภาษาไทย
    return text.replace("ํา", "ำ")


@library
class ocr_keywords:

    @keyword
    def read_amount_from_image(self, image_path, left_frac=0.80, top_frac=0.17, right_frac=0.99, bottom_frac=0.24):
        # default crop targets the "ยอดที่ต้องชำระ" number in the top-right red box
        # (การ์ดขายสินค้า ก่อนกดรับพอดี) บนภาพหน้าต่างขนาด 1602x667 — ถ้าหน้าต่างขนาดต่างไป
        # หรือ layout เปลี่ยน ต้องคำนวณสัดส่วนใหม่
        img = Image.open(image_path)
        width, height = img.size
        box = (
            int(width * left_frac),
            int(height * top_frac),
            int(width * right_frac),
            int(height * bottom_frac),
        )
        cropped = img.crop(box)
        text = pytesseract.image_to_string(
            cropped, config="--psm 7 -c tessedit_char_whitelist=0123456789."
        )
        match = re.search(r"\d+\.?\d*", text)
        if not match:
            raise ValueError(f"Could not read amount from image, OCR text: {text!r}")
        return float(match.group())

    @keyword
    def read_subtotal_from_image(self, image_path, left_frac=0.24, top_frac=0.10, right_frac=0.32, bottom_frac=0.19):
        # default crop targets ตัวเลข "ยอดรวม" (ราคาเต็มก่อนหักส่วนลด) มุมบนซ้าย บนหน้าจอ
        # ชำระเงิน (หลังกด + แล้ว) บนภาพขนาด 1602x667 — วัดพิกัดจากไฟล์ภาพจริงแล้ว (ไม่ใช่ประมาณ)
        # ใช้แทนการอ่านคอลัมน์ "ราคา/หน่วย" ในตารางรายการ เพราะพอกด + ไปหน้าชำระเงินแล้ว
        # ตารางรายการจะไม่แสดงอีกต่อไป แต่ "ยอดรวม" (ราคาเต็ม × จำนวนชิ้น) ยังเห็นอยู่
        img = Image.open(image_path)
        width, height = img.size
        box = (
            int(width * left_frac),
            int(height * top_frac),
            int(width * right_frac),
            int(height * bottom_frac),
        )
        cropped = img.crop(box)
        text = pytesseract.image_to_string(
            cropped, config="--psm 7 -c tessedit_char_whitelist=0123456789."
        )
        match = re.search(r"\d+\.?\d*", text)
        if not match:
            raise ValueError(f"Could not read subtotal from image, OCR text: {text!r}")
        return float(match.group())

    @keyword
    def read_unit_price_from_image(self, image_path, left_frac=0.187, top_frac=0.25, right_frac=0.262, bottom_frac=0.30):
        # default crop targets คอลัมน์ "ราคา/หน่วย" แถวแรกของรายการสินค้า บนภาพขนาด 1602x667
        # ตำแหน่งคอลัมน์ (x) วัดจาก header ของตารางแบบละเอียด แต่ตำแหน่งแถวแรก (y) เป็นค่า
        # ประมาณ ยังไม่เคยวัดกับภาพที่มีข้อมูลแถวจริง ควรตรวจสอบกับการรันจริงอีกครั้ง
        # (ไม่แนะนำให้ใช้ตัวนี้แล้ว — ดู read_subtotal_from_image แทน เพราะตารางรายการ
        # มักไม่แสดงแล้วตอนที่ Pay For Free Item เรียกใช้ หลัง Press Plus Key ไปแล้ว)
        img = Image.open(image_path)
        width, height = img.size
        box = (
            int(width * left_frac),
            int(height * top_frac),
            int(width * right_frac),
            int(height * bottom_frac),
        )
        cropped = img.crop(box)
        text = pytesseract.image_to_string(
            cropped, config="--psm 7 -c tessedit_char_whitelist=0123456789."
        )
        match = re.search(r"\d+\.?\d*", text)
        if not match:
            raise ValueError(f"Could not read unit price from image, OCR text: {text!r}")
        return float(match.group())

    @keyword
    def find_text_offset_from_center(
        self, image_path, target_text, lang="tha+eng",
        left_frac=0.0, top_frac=0.0, right_frac=1.0, bottom_frac=1.0,
    ):
        # หาตำแหน่งข้อความบนภาพด้วย OCR แล้วคืนค่า [dx, dy] จากจุดกึ่งกลางภาพ (ของภาพเต็ม
        # ไม่ใช่ของส่วนที่ครอป) ใช้แทนการเดาพิกัด offset ตายตัว เพราะทำงานถูกต้องไม่ว่า
        # หน้าต่างจะขนาด/ตำแหน่งใดก็ตาม
        #
        # left_frac/top_frac/right_frac/bottom_frac (default = ทั้งภาพ) ใช้จำกัดพื้นที่สแกน
        # OCR ให้แคบลง เพราะถ้าปล่อยให้สแกนทั้งภาพที่มีรูปโฆษณาซับซ้อนปนอยู่ Tesseract อาจ
        # มองข้ามข้อความเล็กๆ บนปุ่มไปเลย (พบเคสจริง: หาปุ่ม "ยืนยัน" ไม่เจอทั้งที่ OCR
        # อ่านได้ถูกต้องเมื่อครอปเฉพาะส่วนปุ่ม)
        #
        # Tesseract แยกอักษรไทยแต่ละตัว (รวมสระ/วรรณยุกต์ที่ประกอบกัน) เป็นคนละ "word" ในผลลัพธ์
        # image_to_data เสมอ (ต่างจาก image_to_string ที่ต่อคำให้ถูกต้อง) จึงต้องรวมตัวอักษร
        # ที่อยู่บรรทัดเดียวกันเข้าด้วยกันก่อน แล้วค่อยหา target_text เป็น substring ของบรรทัดนั้น
        img = Image.open(image_path)
        width, height = img.size
        crop_box = (
            int(width * float(left_frac)),
            int(height * float(top_frac)),
            int(width * float(right_frac)),
            int(height * float(bottom_frac)),
        )
        cropped = img.crop(crop_box)
        crop_left, crop_top = crop_box[0], crop_box[1]
        # ต้องระบุ --psm ชัดเจน (sparse text) ไม่งั้น psm อัตโนมัติ (3) จะหาข้อความที่กระจัดกระจาย
        # อยู่บนหน้าจอ UI ไม่เจอเลย (คืนค่าว่างเปล่า)
        data = pytesseract.image_to_data(cropped, lang=lang, config="--psm 11", output_type=pytesseract.Output.DICT)

        lines = {}
        for i, text in enumerate(data["text"]):
            if not text.strip():
                continue
            key = (data["block_num"][i], data["par_num"][i], data["line_num"][i])
            lines.setdefault(key, []).append(
                {
                    "text": text,
                    "left": data["left"][i],
                    "top": data["top"][i],
                    "right": data["left"][i] + data["width"][i],
                    "bottom": data["top"][i] + data["height"][i],
                }
            )

        # ข้อความเดียวกันอาจปรากฏซ้ำหลายที่บนหน้าจอ (เช่น ปุ่ม "ยืนยัน" ตัวจริง VS ข้อความ
        # แนะนำท้ายจอ "...กดปุ่มยืนยัน") เก็บทุกตำแหน่งที่เจอไว้ก่อน แล้วเลือกอันที่บรรทัด
        # สั้นที่สุด (ใกล้เคียง target_text เดี่ยวๆ ที่สุด) เพราะปุ่มมักมีแค่ข้อความสั้นๆ
        # อยู่บรรทัดเดียวกัน ต่างจากประโยคยาวๆ ที่ฝังคำนั้นอยู่ตรงกลาง
        target_text = _fix_sara_am(target_text)
        candidates = []
        for chars in lines.values():
            line_text = _fix_sara_am("".join(c["text"] for c in chars))
            idx = line_text.find(target_text)
            if idx == -1:
                continue
            matched = chars[idx : idx + len(target_text)]
            left = min(c["left"] for c in matched)
            top = min(c["top"] for c in matched)
            right = max(c["right"] for c in matched)
            bottom = max(c["bottom"] for c in matched)
            candidates.append((len(line_text), left, top, right, bottom))

        if not candidates:
            raise ValueError(f"Text {target_text!r} not found on screen")
        candidates.sort(key=lambda c: c[0])
        _, left, top, right, bottom = candidates[0]
        # บวก crop_left/crop_top กลับเข้าไป เพราะพิกัดที่ OCR คืนมาอ้างอิงจากภาพที่ครอปแล้ว
        # ไม่ใช่ภาพเต็ม ต้องแปลงกลับก่อนคำนวณ offset จากจุดกึ่งกลางของภาพเต็ม
        left, right = left + crop_left, right + crop_left
        top, bottom = top + crop_top, bottom + crop_top
        x = (left + right) / 2
        y = (top + bottom) / 2
        return [int(x - width / 2), int(y - height / 2)]

    @keyword
    def screen_contains_text(self, image_path, target_text, lang="tha+eng"):
        # เช็คว่าข้อความปรากฏอยู่บนภาพหรือไม่ (ไม่คืนตำแหน่ง) ใช้ image_to_string ซึ่งต่อคำ
        # ภาษาไทยให้ถูกต้องกว่า image_to_data จึงเหมาะกับการเช็คการมีอยู่ของข้อความยาวๆ
        img = Image.open(image_path)
        text = pytesseract.image_to_string(img, lang=lang, config="--psm 11")
        return _fix_sara_am(target_text) in _fix_sara_am(text)

    @keyword
    def get_offset_from_fraction(self, image_path, x_frac, y_frac):
        # คำนวณ [dx, dy] จากจุดกึ่งกลางภาพ โดยใช้ขนาดภาพจริง ณ ขณะนั้น (ไม่ใช่ขนาดตายตัว)
        # ใช้แทนพิกัด offset คงที่ เพราะหน้าต่างจริงบางครั้งขนาดไม่ตรงกับที่คำนวณพิกัดไว้ล่วงหน้า
        img = Image.open(image_path)
        width, height = img.size
        dx = int(width * float(x_frac) - width / 2)
        dy = int(height * float(y_frac) - height / 2)
        return [dx, dy]
