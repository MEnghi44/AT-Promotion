# -*- coding: utf-8 -*-
import ctypes
import json
import os
import time
from ctypes import wintypes


class CoordinateRobot(object):
    ROBOT_LIBRARY_SCOPE = 'GLOBAL'

    def __init__(self, credential_file):
        library_directory = os.path.dirname(os.path.abspath(__file__))
        self.credential_file = os.path.abspath(
            os.path.join(library_directory, credential_file))
        try:
            with open(self.credential_file, 'r', encoding='utf-8-sig') as credential_stream:
                self.credentials = json.load(credential_stream)
        except UnicodeDecodeError:
            with open(self.credential_file, 'r', encoding='utf-8', errors='replace') as credential_stream:
                self.credentials = json.load(credential_stream)
        self.user32 = ctypes.windll.user32

    def get_login_value(self, name):
        value = self.credentials
        for key in name.split('.'):
            if key not in value:
                raise AssertionError('Login value is not defined: ' + name)
            value = value[key]
        if value is None:
            raise AssertionError('Login value is not defined: ' + name)
        return value

    def click_at(self, x, y):
        self.user32.SetCursorPos(int(x), int(y))
        # หน่วงสั้นๆ ให้แอปรับรู้ mouseover/hover ก่อนกด - ปุ่ม custom-draw
        # บางตัวเช็คตำแหน่งเมาส์จาก mousemove ก่อนถึงจะยอมรับ click ที่ตามมา
        time.sleep(0.2)
        self.user32.mouse_event(2, 0, 0, 0, 0)
        time.sleep(0.05)
        self.user32.mouse_event(4, 0, 0, 0, 0)
        time.sleep(0.1)

    # ord(character) ใช้เป็น virtual-key code ตรงๆ ได้กับเลข 0-9/ตัวอักษร A-Z
    # เท่านั้น (บังเอิญค่า ASCII ตรงกับ VK code) - ตัวอักษรพิเศษอื่นต้อง map
    # เป็น VK code จริงเอง เช่น '*' ต้องใช้ VK_MULTIPLY (0x6A) ไม่ใช่ ord('*')
    # (0x2A ซึ่งจริงๆคือ VK_SNAPSHOT/Print) ไม่งั้นจะไม่พิมพ์อะไรเลย
    _CHAR_VIRTUAL_KEYS = {
        '*': 0x6A,
    }

    def type_text(self, text):
        for character in text:
            key_code = self._CHAR_VIRTUAL_KEYS.get(character, ord(character))
            self._key_down(key_code)
            self._key_up(key_code)
            time.sleep(0.03)

    def press_enter(self):
        self._press_virtual_key(0x0D)

    def send_keys(self, keys):
        virtual_keys = {
            '{Add}': 0x6B,
            '{Enter}': 0x0D,
            '{Backspace}': 0x08,
            '{Esc}': 0x1B
        }
        if keys not in virtual_keys:
            raise AssertionError('Unsupported key: ' + keys)
        self._press_virtual_key(virtual_keys[keys])

    def press_enter_if_popup_visible(self):
        if self._popup_visible():
            self.press_enter()
            return True
        return False

    def wait_for_popup_and_press_enter(self, timeout=10, interval=0.5):
        deadline = time.time() + float(timeout)
        while time.time() < deadline:
            if self._popup_visible():
                self.press_enter()
                return True
            time.sleep(float(interval))
        return False

    def popup_visible(self):
        return self._popup_visible()

    def wait_for_popup(self, timeout=10, interval=0.5):
        deadline = time.time() + float(timeout)
        while time.time() < deadline:
            if self._popup_visible():
                return True
            time.sleep(float(interval))
        return False

    def press_backspace(self):
        self._press_virtual_key(0x08)

    def capture_current_cursor(self):
        point = wintypes.POINT()
        self.user32.GetCursorPos(ctypes.byref(point))
        return point.x, point.y

    def get_control_text_at(self, x, y):
        """อ่านข้อความจริงจาก native Win32 control ที่อยู่ตำแหน่ง (x, y)

        หาใหม่ทุกครั้งที่เรียก (ไม่แคช) เพราะราคาที่แสดงเปลี่ยนไปทุกแถว ถ้า
        control ที่เจอตรงจุดนั้นไม่มีข้อความ (เช่นเป็น container/panel ที่ครอบ
        อยู่) จะลองหาใน child window ที่ซ้อนอยู่ข้างในบริเวณจุดนั้นต่อ
        คืนค่า '' ถ้าหาไม่พบข้อความจริงเลย (อาจเป็น custom-drawn/canvas
        control ที่วาดตัวเลขเองโดยไม่มี control ข้อความแยกจริง)
        """
        point = wintypes.POINT(int(x), int(y))
        hwnd = self.user32.WindowFromPoint(point)
        if not hwnd:
            return ''
        text = self._get_window_text(hwnd)
        if text:
            return text
        return self._find_text_in_children_at(hwnd, int(x), int(y))

    def get_control_debug_info_at(self, x, y):
        """คืนข้อความอธิบาย control ที่ตำแหน่ง (x, y) สำหรับใส่ใน error message"""
        point = wintypes.POINT(int(x), int(y))
        hwnd = self.user32.WindowFromPoint(point)
        if not hwnd:
            return 'ไม่พบ control ใดๆ ที่ตำแหน่งนี้'
        class_buffer = ctypes.create_unicode_buffer(256)
        self.user32.GetClassNameW(hwnd, class_buffer, 256)
        text = self._get_window_text(hwnd)
        return 'hwnd={0}, class={1}, text={2}'.format(hwnd, class_buffer.value, repr(text))

    def _get_window_text(self, hwnd):
        buffer_length = self.user32.GetWindowTextLengthW(hwnd) + 1
        buffer = ctypes.create_unicode_buffer(buffer_length)
        self.user32.GetWindowTextW(hwnd, buffer, buffer_length)
        return buffer.value

    def _find_text_in_children_at(self, hwnd, x, y):
        found = ['']

        @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
        def enum_callback(child_hwnd, _lparam):
            rect = wintypes.RECT()
            if not self.user32.GetWindowRect(child_hwnd, ctypes.byref(rect)):
                return True
            if rect.left <= x <= rect.right and rect.top <= y <= rect.bottom:
                text = self._get_window_text(child_hwnd)
                if text:
                    found[0] = text
                    return False
            return True

        self.user32.EnumChildWindows(hwnd, enum_callback, 0)
        return found[0]

    def get_pixel_color(self, x, y):
        """อ่านสี (r, g, b) ของพิกเซลบนหน้าจอที่ตำแหน่ง (x, y)

        ใช้ตรวจสอบสถานะหน้าจอแทนการอ่านข้อความ สำหรับแอปที่วาดเองทั้งหมด
        (custom-drawn) จนอ่าน text ผ่าน Windows API ไม่ได้เลย
        """
        screen_dc = self.user32.GetDC(0)
        try:
            pixel = ctypes.windll.gdi32.GetPixel(screen_dc, int(x), int(y))
        finally:
            self.user32.ReleaseDC(0, screen_dc)
        red = pixel & 255
        green = (pixel >> 8) & 255
        blue = (pixel >> 16) & 255
        return red, green, blue

    def _press_virtual_key(self, key_code):
        self.user32.keybd_event(key_code, 0, 0, 0)
        self.user32.keybd_event(key_code, 0, 2, 0)

    def _key_down(self, key_code):
        self.user32.keybd_event(key_code, 0, 0, 0)

    def _key_up(self, key_code):
        self.user32.keybd_event(key_code, 0, 2, 0)

    def _popup_visible(self):
        screen_dc = self.user32.GetDC(0)
        try:
            sample_points = ((200, 250), (400, 250), (600, 250),
                             (200, 300), (400, 300), (600, 300))
            yellow_points = 0
            for x, y in sample_points:
                pixel = ctypes.windll.gdi32.GetPixel(screen_dc, x, y)
                red = pixel & 255
                green = (pixel >> 8) & 255
                blue = (pixel >> 16) & 255
                if red > 220 and green > 220 and blue < 210:
                    yellow_points += 1
            return yellow_points >= 4
        finally:
            self.user32.ReleaseDC(0, screen_dc)
