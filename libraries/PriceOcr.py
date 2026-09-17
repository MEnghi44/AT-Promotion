# -*- coding: utf-8 -*-
"""OCR สำหรับอ่าน "ยอดที่ต้องชำระ" จากหน้าชำระเงิน (หน้า B) ของโปร Amount Off
เท่านั้น - ใช้ pixel-template matching เอง (ไม่พึ่ง PIL/numpy เพราะ POS รัน
Python 3.4.4 แบบ offline pip install)

วิธีอ่าน: สแกนหาคอลัมน์ในกรอบที่กำหนด (amount_due_field) ที่มีสีต่างจากพื้น
หลัง (ocr_background_rgb, calibrate ไว้ล่วงหน้า) ไปเรื่อยๆ กลุ่มคอลัมน์ที่
ติดกันคือ 1 ตัวอักษร (segmentation) แล้วเทียบแต่ละตัวอักษรกับ template ที่
calibrate ไว้ล่วงหน้า (ตัวเลข 0-9 และ '.') ด้วย Hamming distance บน grid
บิตที่ normalize ขนาดเท่ากันทุกตัว (กันปัญหาความกว้าง/สูงจริงของแต่ละตัว
อักษรไม่เท่ากันเป๊ะทุกครั้งที่อ่าน)
"""
import json
import os


class PriceOcr(object):
    _OCR_GRID_W = 6
    _OCR_GRID_H = 10
    _OCR_COLOR_DISTANCE_THRESHOLD = 60

    def _ocr_templates_path(self):
        return os.path.abspath(
            os.path.join(self.library_directory, '..', 'data', 'price_ocr_templates.json'))

    def _load_price_ocr_templates(self):
        if getattr(self, '_price_ocr_templates', None) is None:
            path = self._ocr_templates_path()
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    self._price_ocr_templates = json.load(f)
            else:
                self._price_ocr_templates = {}
        return self._price_ocr_templates

    def _save_price_ocr_templates(self):
        path = self._ocr_templates_path()
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(self._load_price_ocr_templates(), f, ensure_ascii=False, indent=2)

    def set_price_ocr_background(self, x, y):
        """calibrate: เอาเมาส์ไปวางบนพื้นหลังว่างๆในกรอบ amount_due_field
        (ตรงไหนก็ได้ที่ไม่มีตัวเลขทับ) แล้วเรียก keyword นี้ครั้งเดียว
        """
        red, green, blue = self.robot.get_pixel_color(x, y)
        self.settings['ocr_background_rgb'] = (red, green, blue)
        return True

    def _ocr_background_rgb(self):
        rgb = self.settings.get('ocr_background_rgb')
        if not rgb:
            raise AssertionError('ยังไม่ได้ calibrate สีพื้นหลัง OCR (ocr_background_rgb)')
        return rgb

    def _is_ocr_foreground(self, rgb):
        bg = self._ocr_background_rgb()
        distance = sum((a - b) ** 2 for a, b in zip(rgb, bg)) ** 0.5
        return distance > self._OCR_COLOR_DISTANCE_THRESHOLD

    def _sample_grid(self, region_pixels, grid_w, grid_h):
        height = len(region_pixels)
        width = len(region_pixels[0]) if height else 0
        grid = []
        for gy in range(grid_h):
            row_bits = []
            for gx in range(grid_w):
                src_x = min(width - 1, int(gx * width / grid_w))
                src_y = min(height - 1, int(gy * height / grid_h))
                row_bits.append(1 if self._is_ocr_foreground(region_pixels[src_y][src_x]) else 0)
            grid.append(row_bits)
        return grid

    def capture_price_digit_template(self, digit, x, y, width, height):
        """calibrate: เอาเมาส์ไปวางที่มุมบนซ้ายของตัวอักษร (digit) ตัวเดียว
        บนหน้าจอจริง (เช่นเลข "3" ในยอด "31.00") แล้วระบุ width/height ที่
        ครอบตัวอักษรนั้นพอดี - เรียกทีละตัวให้ครบ 0-9 และ '.' ก่อนใช้งานจริง
        บันทึกลงไฟล์ data/price_ocr_templates.json ทันที (ใช้ข้ามรอบรันได้)
        """
        region = self.robot.get_pixel_region(x, y, width, height)
        grid = self._sample_grid(region, self._OCR_GRID_W, self._OCR_GRID_H)
        templates = self._load_price_ocr_templates()
        templates[str(digit)] = grid
        self._save_price_ocr_templates()
        return True

    def _match_grid_to_char(self, grid):
        templates = self._load_price_ocr_templates()
        if not templates:
            raise AssertionError('ยังไม่ได้ calibrate price digit template เลย (ว่างอยู่)')
        best_char, best_distance = None, None
        for char, template_grid in templates.items():
            distance = sum(
                1 for row_a, row_b in zip(grid, template_grid)
                for a, b in zip(row_a, row_b) if a != b)
            if best_distance is None or distance < best_distance:
                best_char, best_distance = char, distance
        return best_char

    def _segment_field_region(self, x, y, width, height):
        region = self.robot.get_pixel_region(x, y, width, height)
        col_is_fg = []
        for col in range(width):
            has_fg = any(self._is_ocr_foreground(region[row][col]) for row in range(height))
            col_is_fg.append(has_fg)

        segments = []
        start = None
        for col, is_fg in enumerate(col_is_fg):
            if is_fg and start is None:
                start = col
            elif not is_fg and start is not None:
                segments.append((start, col))
                start = None
        if start is not None:
            segments.append((start, width))
        return region, segments

    def read_amount_due_from_screen(self):
        """อ่านค่า "ยอดที่ต้องชำระ" จากหน้าชำระเงิน (หน้า B) ตามกรอบที่ตั้งไว้
        (amount_due_field: x, y และ amount_due_field_size: width, height)
        """
        x, y = self.get_new_price_coordinate('amount_due_field')
        width, height = self.get_new_price_coordinate('amount_due_field_size')
        region, segments = self._segment_field_region(x, y, int(width), int(height))
        if not segments:
            raise AssertionError('OCR ไม่พบตัวเลขในบริเวณ "ยอดที่ต้องชำระ" ที่กำหนด (พื้นหลังล้วน)')

        chars = []
        for seg_start, seg_end in segments:
            sub_region = [row[seg_start:seg_end] for row in region]
            grid = self._sample_grid(sub_region, self._OCR_GRID_W, self._OCR_GRID_H)
            chars.append(self._match_grid_to_char(grid))

        text = ''.join(chars)
        try:
            return float(text)
        except ValueError:
            raise AssertionError(
                'OCR อ่านค่า "ยอดที่ต้องชำระ" ไม่เป็นตัวเลข: {0} (segments={1})'.format(
                    text, segments))
