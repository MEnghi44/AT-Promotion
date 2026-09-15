# -*- coding: utf-8 -*-
"""ทดสอบโปรโมชัน "Free Item" (ซื้อ trigger_value ชิ้น ฟรี 1 ชิ้นตายตัว)

โครงสร้างการทำงานทั้งหมด (สแกน, จัดการ popup, จับคู่ bucketid tier, log
ผลลัพธ์) เหมือนกับ NewPriceRobot (New Price) 100% ต่างกันแค่สูตรเช็คราคา
เพราะ Free Item ไม่มี reward_value (ราคาพิเศษ) ให้เทียบตรงๆ - จึงสืบทอด
(subclass) มาจาก NewPriceRobot แทนการก็อปปี้โค้ดซ้ำ แก้ทีเดียวจบทั้งคู่
ถ้าเป็นส่วนที่ใช้ร่วมกัน (สแกน/popup/log ฯลฯ)
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from NewPriceRobot import NewPriceRobot


class FreeItemRobot(NewPriceRobot):
    ROBOT_LIBRARY_SCOPE = 'GLOBAL'

    def new_price_matches_reward(self, index, pos_price, first_item=None):
        """Free Item: reward_value ว่างเสมอ (ไม่มีราคาพิเศษ) - โปรแบบนี้คือ
        "ซื้อ trigger_value ชิ้น ฟรี 1 ชิ้น" เสมอ (ไม่ว่า trigger_value จะ
        เป็นเท่าไหร่ ฟรีแค่ 1 ชิ้นตายตัว) ราคาที่ต้องจ่ายจริงจึงคำนวณจาก
        (trigger_value - 1) x ราคาต่อหน่วยจริง (item_price จาก LPE
        breakdown หลังปิดบิล - ไม่มี field ราคาต่อหน่วยที่ใช้ได้ตรงๆใน
        local db) แทนการเทียบ reward_value ตรงๆแบบ New Price
        """
        row = self._get_row(index)
        try:
            pos_value = float(pos_price)
        except (TypeError, ValueError):
            return False

        trigger_raw = row.get('trigger_value')
        try:
            trigger_value = int(float(trigger_raw)) if trigger_raw not in (None, '') else 1
        except ValueError:
            trigger_value = 1

        try:
            item_price = float(str((first_item or {}).get('item_price', '')).strip())
        except (TypeError, ValueError):
            return False

        expected = (trigger_value - 1) * item_price
        return abs(expected - pos_value) < 0.01
