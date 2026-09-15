# -*- coding: utf-8 -*-
"""สคริปต์ช่วยเหลือแยกเดี่ยว (ไม่ใช่ Robot library) โชว์พิกัดเมาส์แบบ real-time

รันด้วย: C:\\Python34\\python.exe show_cursor_position.py
เอาเมาส์ไปวางที่ปุ่ม/ช่องแต่ละอันบนหน้าจอ POS แล้วอ่านค่า x,y ที่ขึ้นใน
console เอาไปกรอกใน resources/new_price_keywords.robot
กด Ctrl+C เพื่อหยุด
"""
import ctypes
import time
from ctypes import wintypes

user32 = ctypes.windll.user32


def get_cursor_pos():
    point = wintypes.POINT()
    user32.GetCursorPos(ctypes.byref(point))
    return point.x, point.y


if __name__ == '__main__':
    print('เอาเมาส์ไปวางที่ปุ่ม/ช่องบนหน้าจอ POS กด Ctrl+C เพื่อหยุด')
    try:
        while True:
            x, y = get_cursor_pos()
            print('\rx={0}, y={1}          '.format(x, y), end='')
            time.sleep(0.15)
    except KeyboardInterrupt:
        print()
