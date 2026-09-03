import ctypes

import psutil
import win32gui
import win32process
from robot.api.deco import keyword, library


@library
class window_keywords:

    @keyword
    def arrange_windows_side_by_side(self, vnc_executable="vncviewer.exe"):
        # จัดหน้าต่าง cmd (ที่รัน robot อยู่) กับหน้าต่าง VNC ให้อยู่คนละฝั่งของจอ กันทับกัน
        #
        # สำคัญ: ห้าม resize หน้าต่าง VNC เด็ดขาด เพราะ Click Exact Payment/Click Member Button
        # ใน pos_keywords.robot ใช้ "พิกัดพิกเซลตายตัว" (offset:-211,-25 ฯลฯ) ที่ calibrate ไว้
        # เฉพาะกับขนาดหน้าต่าง VNC ตอนเปิดปกติ (1602x667) เท่านั้น ถ้า resize พิกัดพวกนี้จะผิด
        # ทันที คลิกพลาดตำแหน่งตอนจ่ายเงิน/ยืนยันสมาชิก จึงแค่ "ย้ายตำแหน่ง" หน้าต่าง VNC ไปมุม
        # จอ โดยคงขนาดเดิมไว้ทั้งหมด แล้วค่อย resize เฉพาะหน้าต่าง cmd ให้พอดีกับพื้นที่ที่เหลือแทน
        # (หน้าต่าง cmd ไม่มี automation ใดอิงพิกัดตายตัวกับมัน resize ได้อย่างปลอดภัย)
        user32 = ctypes.windll.user32
        screen_w = user32.GetSystemMetrics(0)
        screen_h = user32.GetSystemMetrics(1)

        vnc_hwnd = self._find_window_by_process(vnc_executable)
        if vnc_hwnd:
            left, top, right, bottom = win32gui.GetWindowRect(vnc_hwnd)
            vnc_width = right - left
            vnc_height = bottom - top
            vnc_x = screen_w - vnc_width
            win32gui.MoveWindow(vnc_hwnd, vnc_x, 0, vnc_width, vnc_height, True)
        else:
            vnc_x = screen_w

        console_hwnd = ctypes.windll.kernel32.GetConsoleWindow()
        if console_hwnd:
            win32gui.MoveWindow(console_hwnd, 0, 0, vnc_x, screen_h, True)

    def _find_window_by_process(self, exe_name):
        # หา window handle ของโปรแกรมจากชื่อ .exe (ไม่ใช่ title เพราะ title ของ vncviewer.exe
        # เปลี่ยนไปตาม server ที่เชื่อมต่อ ระบุด้วยชื่อโปรแกรมแน่นอนกว่า)
        matches = []

        def callback(hwnd, _):
            if not win32gui.IsWindowVisible(hwnd):
                return True
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            try:
                if psutil.Process(pid).name().lower() == exe_name.lower():
                    matches.append(hwnd)
            except psutil.NoSuchProcess:
                pass
            return True

        win32gui.EnumWindows(callback, None)
        return matches[0] if matches else None
