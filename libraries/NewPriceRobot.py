# -*- coding: utf-8 -*-
import json
import os
import re
import sqlite3
import sys
import time
import urllib.request
from datetime import datetime
from robot.api import logger

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from CoordinateRobot import CoordinateRobot
from PosSqlClient import PosSqlClient


class NewPriceRobot(PosSqlClient):
    ROBOT_LIBRARY_SCOPE = 'GLOBAL'

    LPE_RULE_COLUMNS = [
        'rule_id', 'prom_desc', 'rule_name', 'unit', 'unitru', 'price', 'unit2',
        'sumamt', 'unitamt', 'type', 'mmbr_id', 'rwrd_mmbr',
    ]
    LPE_ITEM_COLUMNS = [
        'product_code', 'product_name', 'item_price', 'item_qty', 'item_total_amt',
        'item_reware', 'qty_s', 'unit_t', 'targets',
    ]
    RESULT_COLUMNS = [
        'promotion_code', 'promotion_name', 'active_from', 'active_to',
        'redemption_limit_per_transaction', 'bucketid', 'trigger_value',
        'entity_code', 'entity_name',
        'barcode_used', 'reward_value', 'notes', 'sheet', 'worksheet',
        'receipt_no', 'pos_no',
        'rule_id', 'prom_desc', 'rule_name', 'pos_price',
        'unit', 'unitru', 'price', 'unit2', 'sumamt', 'unitamt', 'type',
        'mmbr_id', 'rwrd_mmbr',
    ] + LPE_ITEM_COLUMNS + [
        'result', 'remark', 'executed_at',
    ]
    HEADER_LABELS = {
        'barcode_used': 'barcode',
        'receipt_no': 'RECEIPT_NO',
        'pos_no': 'POS_NO',
        'rule_id': 'RULE_ID',
        'prom_desc': 'PROM_DESC',
        'rule_name': 'RULE_NAME',
        'unit': 'UNIT',
        'unitru': 'UNITRU',
        'price': 'PRICE',
        'unit2': 'UNIT2',
        'sumamt': 'SUMAMT',
        'unitamt': 'UNITAMT',
        'type': 'TYPE',
        'mmbr_id': 'MMBR_ID',
        'rwrd_mmbr': 'RWRD_MMBR',
        'product_code': 'PRODUCT_CODE',
        'product_name': 'PRODUCT_NAME',
        'item_price': 'PRICE',
        'item_qty': 'QTY',
        'item_total_amt': 'TOTAL_AMT',
        'item_reware': 'REWARE',
        'qty_s': 'QTY_S',
        'unit_t': 'UNI_T',
        'targets': 'TARGETS',
    }

    def __init__(self, credential_file):
        self.library_directory = os.path.dirname(os.path.abspath(__file__))
        self.credential_file = os.path.abspath(
            os.path.join(self.library_directory, credential_file))
        try:
            with open(self.credential_file, 'r', encoding='utf-8-sig') as credential_stream:
                self.credentials = json.load(credential_stream)
        except UnicodeDecodeError:
            with open(self.credential_file, 'r', encoding='utf-8', errors='replace') as credential_stream:
                self.credentials = json.load(credential_stream)
        self.rows = []
        self.log_rows = []
        self.worksheet_name = ''
        self.start_row = 0
        self.end_row = 0
        self.robot = CoordinateRobot(credential_file)
        self.coordinates = {}
        self.price_point = None
        self.settings = {}
        self._sql_baseline_receipt_no = None
        self.last_receipt_no = ''
        self.last_lpe_combos = [({}, {})]

    # ------------------------------------------------------------------
    # ตัวช่วยอ่าน config
    # พิกัด/จุดอ่านราคา/เวลารอ มาจากไฟล์ .robot (Variables + keyword Set New
    # Price ... ด้านล่าง) ไม่ได้มาจาก JSON config
    # ------------------------------------------------------------------
    def _new_price_config(self):
        return self.credentials.get('new_price', {})

    def set_new_price_setting(self, name, value):
        self.settings[name] = value
        return True

    def get_new_price_setting(self, name, default=None):
        if name in self.settings:
            return self.settings[name]
        value = self._new_price_config().get(name, default)
        if value is None:
            raise AssertionError('New price setting is not defined: ' + name)
        return value

    def set_new_price_coordinate(self, name, x, y):
        self.coordinates[name] = (int(x), int(y))
        return True

    def get_new_price_coordinate(self, name):
        point = self.coordinates.get(name)
        if not point:
            raise AssertionError('Coordinate is not configured: ' + name)
        if point == (0, 0):
            raise AssertionError('Coordinate is not calibrated yet: ' + name)
        return point

    def set_new_price_price_point(self, x, y):
        self.price_point = (int(x), int(y))
        return True

    def _is_invalid_barcode_popup_visible(self):
        """เช็ค popup "รหัสบาร์โค้ดไม่ถูกต้อง" (พื้นเหลือง) ด้วยสีพิกเซล
        แทนข้อความ (แอปนี้ custom-drawn อ่าน text ผ่าน Windows API ไม่ได้)
        - ถ้ายังไม่ได้ calibrate จุดนี้ ถือว่าไม่เจอ popup เสมอ (ปิด
        feature นี้ไว้จนกว่าจะตั้งพิกัด ไม่ให้กระทบ flow เดิม)
        """
        try:
            x, y = self.get_new_price_coordinate('invalid_barcode_popup_point')
        except AssertionError:
            return False, None
        red, green, blue = self.robot.get_pixel_color(x, y)
        is_yellow = red > 200 and green > 200 and blue < 180
        return is_yellow, (red, green, blue)

    def _clear_barcode_input(self, delay):
        self.robot.click_at(*self.get_new_price_coordinate('barcode_input'))
        time.sleep(delay)
        for _ in range(30):
            self.robot.send_keys('{Backspace}')

    def _scan_barcode_and_check(self, index, barcode_str, delay):
        """คลิกช่อง input, พิมพ์บาร์โค้ด, Enter แล้วเช็คว่า POS ขึ้น popup
        "รหัสบาร์โค้ดไม่ถูกต้อง" ไหม - ถ้าขึ้น: กด Esc ออกจาก popup, ลบ
        บาร์โค้ดที่พิมพ์ค้างในช่อง input ออกให้หมด แล้ว raise AssertionError
        (ทำให้แถวนี้ Fail และข้ามไปแถวถัดไปทันที ไม่ไปต่อขั้นตอนอื่น)
        """
        self.robot.click_at(*self.get_new_price_coordinate('barcode_input'))
        time.sleep(delay)
        self._log_step(index, 'Type barcode: {0}'.format(barcode_str))
        self.robot.type_text(barcode_str)
        self.robot.press_enter()
        time.sleep(delay)
        is_invalid, rgb = self._is_invalid_barcode_popup_visible()
        if is_invalid:
            self._log_step(
                index, 'Invalid barcode popup detected for {0} (rgb={1})'.format(
                    barcode_str, rgb))
            self.robot.send_keys('{Esc}')
            time.sleep(delay)
            self._clear_barcode_input(delay)
            raise AssertionError(
                'popup รหัสบาร์โค้ดไม่ถูกต้อง (Invalid Barcode): {0}'.format(barcode_str))

    def _is_mstamp_choice_popup_visible(self):
        """เช็ค popup "สอบถามลูกค้าว่าต้องการรับ M-Stamp หรือแสตมป์" (พื้น
        เหลืองเหมือน popup รหัสบาร์โค้ดไม่ถูกต้อง) ด้วยสีพิกเซล - ถ้ายังไม่ได้
        calibrate จุดนี้ ถือว่าไม่เจอ popup เสมอ (ปิด feature ไว้จนกว่าจะตั้ง
        พิกัด ไม่ให้กระทบ flow เดิม)
        """
        try:
            x, y = self.get_new_price_coordinate('mstamp_popup_check_point')
        except AssertionError:
            return False, None
        red, green, blue = self.robot.get_pixel_color(x, y)
        is_yellow = red > 200 and green > 200 and blue < 180
        return is_yellow, (red, green, blue)

    def _handle_mstamp_choice_popup(self, index, delay):
        """หลังกด "ใช่" ยืนยัน popup รับพอดีแล้ว บางโปรจะมี popup ถามต่อว่า
        จะรับเป็น M-Stamp หรือแสตมป์ - ถ้าขึ้น popup นี้ ให้กดปุ่ม M-Stamp
        เสมอ แล้วขายต่อไปตามปกติ (ไม่ใช่ error ไม่ทำให้แถว Fail)
        """
        is_visible, rgb = self._is_mstamp_choice_popup_visible()
        if not is_visible:
            return
        self._log_step(
            index, 'M-Stamp/stamp choice popup detected (rgb={0}) - clicking M-Stamp'.format(rgb))
        try:
            mstamp_point = self.get_new_price_coordinate('mstamp_button')
        except AssertionError as exc:
            self._log_step(
                index, 'WARNING: mstamp_popup_check_point is calibrated but mstamp_button '
                'is not - cannot click M-Stamp ({0})'.format(exc))
            return
        self.robot.click_at(*mstamp_point)
        time.sleep(delay)

    def _resolve_database_path(self):
        db_path = self.credentials.get('database_file')
        if not db_path:
            raise AssertionError('database_file is not defined in config')
        return os.path.abspath(os.path.join(self.library_directory, db_path))

    # ------------------------------------------------------------------
    # โหลดข้อมูล
    # ------------------------------------------------------------------
    def load_new_price_rows(self):
        cfg = self._new_price_config()
        reward_type = cfg.get('reward_type', 'New Price')
        worksheet = cfg.get('worksheet')
        sheet = cfg.get('sheet')
        active_from = cfg.get('active_from')
        start_row = int(cfg.get('start_row', 2))
        end_row = int(cfg.get('end_row', start_row))

        conditions = ['reward_type = ?']
        params = [reward_type]
        if worksheet:
            worksheet_list = worksheet if isinstance(worksheet, list) else [worksheet]
            conditions.append(
                'worksheet IN ({0})'.format(', '.join('?' for _ in worksheet_list)))
            params.extend(worksheet_list)
        if sheet:
            sheet_list = sheet if isinstance(sheet, list) else [sheet]
            conditions.append(
                'sheet IN ({0})'.format(', '.join('?' for _ in sheet_list)))
            params.extend(sheet_list)
        if active_from:
            conditions.append('active_from = ?')
            params.append(active_from)

        conn = sqlite3.connect(self._resolve_database_path())
        conn.row_factory = sqlite3.Row
        try:
            cur = conn.cursor()
            cur.execute(
                'SELECT * FROM promotion_data WHERE {0} ORDER BY rowid'.format(
                    ' AND '.join(conditions)),
                params)
            all_rows = [dict(row) for row in cur.fetchall()]
        finally:
            conn.close()

        # start_row/end_row คือลำดับแบบ 1-based ธรรมดา นับจากแถวที่กรองแล้ว
        # (ตาม reward_type + worksheet) start_row=1 คือแถวข้อมูลแถวแรก
        first_index = start_row - 1
        last_index = end_row - 1
        if first_index < 0 or last_index < first_index:
            raise AssertionError(
                'ช่วง start_row/end_row ไม่ถูกต้อง: {0}-{1}'.format(start_row, end_row))
        if first_index >= len(all_rows):
            raise AssertionError(
                'ไม่พบข้อมูล New Price ในช่วง start_row/end_row ที่กำหนด '
                '(พบทั้งหมด {0} แถวสำหรับ worksheet นี้)'.format(len(all_rows)))

        self.rows = all_rows[first_index:last_index + 1]
        # worksheet อาจไม่ได้ตั้งใน config แล้ว (ใช้ sheet กรองแทน) - เอาค่า
        # worksheet จริงจากแถวข้อมูลที่โหลดมาได้เลย ไม่ต้องพึ่ง config -
        # worksheet ใน config อาจเป็น list ได้ (กรองหลายค่า) ต้อง join เป็น
        # string ก่อนใช้แสดงผล/ตั้งชื่อไฟล์ ไม่งั้น openpyxl เขียนไม่ได้
        if isinstance(worksheet, list):
            worksheet_display = ', '.join(worksheet)
        else:
            worksheet_display = worksheet
        self.worksheet_name = worksheet_display or self.rows[0].get('worksheet', '') or ''
        self.start_row = start_row
        self.end_row = end_row
        return len(self.rows)

    def get_new_price_row_count(self):
        return len(self.rows)

    def _build_new_price_bill_plans(self):
        """จัดกลุ่มแถวที่โหลดมาแล้ว (self.rows) ตาม promotion_code แล้วตาม
        bucketid - promotion_code ที่มีหลาย bucketid tier (1,2,3,...) ต้อง
        จับคู่แถวจากแต่ละ tier ตามตำแหน่ง (tier1 แถวที่ 1 คู่กับ tier2 แถว
        ที่ 1, tier1 แถวที่ 2 คู่กับ tier2 แถวที่ 2, ...) มาสแกนรวมในบิล
        เดียวกัน โดยแถว tier สูงสุดที่มีอยู่ในบิลนั้นเป็นแถวที่ถูกทดสอบ
        จริง (เทียบ reward_value ของแถวนั้นเดียว ไม่บวกกับ tier อื่น) ส่วน
        tier ต่ำกว่าเป็นแค่ตัวช่วยสแกนให้เข้าเงื่อนไข

        จำนวนบิลทั้งหมดของ promotion_code นั้น = จำนวนแถวของ tier ที่มาก
        ที่สุด (ไม่ใช่ผลรวมทุก tier) - tier ที่แถวน้อยกว่าเมื่อใช้จนหมดแล้ว
        บิลที่เหลือจะมีแค่ tier สูงกว่าเพียวๆ (ไม่มี helper ให้จับคู่)

        คืนค่า list ของ dict {'tested_index': ..., 'helper_indices': [...]}
        - index ที่ใช้คือลำดับ 1-based ตรงกับ _get_row(index)
        """
        promo_groups = {}
        promo_order = []
        for position, row in enumerate(self.rows, start=1):
            promo_code = row.get('promotion_code')
            bucket_raw = row.get('bucketid')
            try:
                bucketid = int(float(bucket_raw)) if bucket_raw not in (None, '') else 1
            except ValueError:
                bucketid = 1
            if promo_code not in promo_groups:
                promo_groups[promo_code] = {}
                promo_order.append(promo_code)
            promo_groups[promo_code].setdefault(bucketid, []).append(position)

        bill_plans = []
        for promo_code in promo_order:
            tiers = promo_groups[promo_code]
            bucket_ids = sorted(tiers.keys())
            if len(bucket_ids) <= 1:
                for position in tiers[bucket_ids[0]]:
                    bill_plans.append({'tested_index': position, 'helper_indices': []})
                continue
            # tier ที่มีแถวน้อยกว่า tier ที่มากที่สุด ให้วนกลับไปเอาแถว
            # แรกๆของ tier นั้นมาจับคู่ซ้ำ (wrap around) จนกว่า tier ที่มาก
            # ที่สุดจะครบ - ไม่ปล่อยให้บิลท้ายๆเป็น tier เดียวโดดๆ
            max_count = max(len(tiers[b]) for b in bucket_ids)
            for pos in range(max_count):
                present = [(b, tiers[b][pos % len(tiers[b])]) for b in bucket_ids]
                tested_index = present[-1][1]
                helper_indices = [position for _, position in present[:-1]]
                bill_plans.append({'tested_index': tested_index, 'helper_indices': helper_indices})
        return bill_plans

    def _get_row(self, index):
        row_index = int(index) - 1
        if row_index < 0 or row_index >= len(self.rows):
            raise AssertionError('New price row index out of range: {0}'.format(index))
        return self.rows[row_index]

    def get_new_price_field(self, index, field_name):
        row = self._get_row(index)
        if field_name not in row:
            raise AssertionError('New price row has no field: ' + field_name)
        return row[field_name]

    @staticmethod
    def _normalize_segment_text(text):
        return re.sub(r'[^0-9A-Za-zก-๏]+', '', text or '').lower()

    def is_new_price_member_segment(self, index, expected_text):
        row = self._get_row(index)
        return self._normalize_segment_text(row.get('member_segmentation')) == \
            self._normalize_segment_text(expected_text)

    def new_price_matches_reward(self, index, pos_price, first_item=None):
        """pos_price ต้องตรงกับ reward_value (ราคาพิเศษ) เป๊ะ - first_item
        รับไว้เฉยๆเพื่อให้ signature ตรงกับ subclass ที่ override สูตรนี้
        (เช่น FreeItemRobot) ตัว base class นี้ (New Price) ไม่ได้ใช้
        """
        row = self._get_row(index)
        try:
            reward_value = float(str(row.get('reward_value', '')).replace(',', ''))
            pos_value = float(pos_price)
        except (TypeError, ValueError):
            return False
        return abs(reward_value - pos_value) < 0.01

    def new_price_matches_rule(self, index, rule):
        """เช็คว่าโปรที่ POS ยิงจริง (RULE_ID/RULE_NAME จาก LPE SQL) ตรงกับ
        promotion_code/promotion_name ที่ตั้งใจทดสอบไว้ในแถวนี้จริง - กัน
        กรณีราคาบังเอิญตรงแต่โปรที่เข้าจริงเป็นคนละตัว

        - promotion_code / RULE_ID: เทียบตรงๆ (ตัวเชื่อม/link หลักระหว่าง
          local db กับ SQL Server)
        - promotion_name / RULE_NAME: เทียบแบบ "link" (คลุม/contains) ไม่ใช่
          เท่ากันตรงตัว เพราะเจอจริงว่า RULE_NAME จาก SQL Server มักตัดคำ
          ต่อท้าย (เช่น "2แถม1") ออกจาก promotion_name ทั้งที่โปรถูกตัวจริง
          - ผ่านถ้า RULE_NAME เป็นส่วนหนึ่งของ promotion_name (หรือกลับกัน)
        """
        row = self._get_row(index)
        expected_code = str(row.get('promotion_code', '')).strip()
        actual_code = str((rule or {}).get('rule_id', '')).strip()
        if expected_code != actual_code:
            return False

        expected_name = str(row.get('promotion_name', '')).strip()
        actual_name = str((rule or {}).get('rule_name', '')).strip()
        if not expected_name or not actual_name:
            return False
        return actual_name in expected_name or expected_name in actual_name

    # ------------------------------------------------------------------
    # บาร์โค้ด
    # ------------------------------------------------------------------
    def compute_new_price_barcode(self, index):
        return self._compute_barcode_for_row(self._get_row(index))

    @staticmethod
    def _compute_barcode_for_row(row):
        barcode = (row.get('barcode') or '').strip()
        if not barcode:
            raise AssertionError('Row has no barcode (entity_code={0})'.format(
                row.get('entity_code')))

        trigger_raw = row.get('trigger_value')
        try:
            trigger_value = int(float(trigger_raw)) if trigger_raw not in (None, '') else 1
        except ValueError:
            trigger_value = 1

        if trigger_value > 1:
            return '{0}*{1}'.format(trigger_value, barcode)
        return barcode


    # ------------------------------------------------------------------
    # บาร์โค้ดสมาชิก (ดึงจาก HTTP API)
    # ------------------------------------------------------------------
    def fetch_member_barcode(self):
        url = self.credentials.get('member_api', {}).get('url')
        if not url:
            raise AssertionError('member_api.url is not defined in config')
        try:
            response = urllib.request.urlopen(url, timeout=10)
            raw = response.read().decode('utf-8')
            data = json.loads(raw)
            barcode = data.get('barcode')
        except Exception as exc:
            raise AssertionError('Gen barcode สมาชิกไม่สำเร็จ: ' + str(exc))
        if not barcode:
            raise AssertionError('Gen barcode สมาชิกไม่สำเร็จ: ไม่พบค่า barcode ใน response')
        return str(barcode)

    # ------------------------------------------------------------------
    # อ่านราคาจากหน้าจอ (สำรอง - ใช้ไม่ได้กับแอปนี้เพราะ custom-drawn ทั้งหมด
    # เก็บโค้ดไว้เผื่ออนาคตเปลี่ยนไปใช้กับ POS ตัวอื่นที่อ่าน text ได้จริง)
    # ------------------------------------------------------------------
    def read_price_from_screen(self):
        if not self.price_point:
            raise AssertionError('price_point ยังไม่ได้ตั้งค่า (ต้อง calibrate ก่อน)')
        x, y = self.price_point
        if (x, y) == (0, 0):
            raise AssertionError('price_point ยังไม่ได้ calibrate')
        text = self.robot.get_control_text_at(x, y)
        digits = re.sub(r'[^0-9.]', '', text.replace(',', ''))
        if not digits:
            debug_info = self.robot.get_control_debug_info_at(x, y)
            raise AssertionError(
                'อ่านข้อความจากตัวควบคุมที่จุดนี้ไม่พบตัวเลขราคา (text={0}, {1})'.format(
                    repr(text), debug_info))
        return float(digits)

    def wait_for_popup_button(self, timeout=10, interval=2.0):
        """รอจนกว่าปุ่ม "ใช่" ของ popup ยืนยันมีข้อความจริงปรากฏขึ้น

        เช็คข้อความจริงจากจุด popup_confirm_yes_button แทนการเดาสีพิกเซลแบบ
        เดิม (ซึ่งเขียนไว้สำหรับ popup คนละแบบตอน login ตำแหน่ง/ขนาดไม่ตรงกัน)
        """
        x, y = self.get_new_price_coordinate('popup_confirm_yes_button')
        deadline = time.time() + float(timeout)
        while time.time() < deadline:
            if self.robot.get_control_text_at(x, y).strip():
                return True
            time.sleep(float(interval))
        return False

    # ------------------------------------------------------------------
    # บันทึกผลทดสอบ (ไฟล์ xlsx)
    # ------------------------------------------------------------------
    def init_new_price_log(self):
        self.log_rows = []
        return True

    def log_new_price_result(self, index, barcode_used, pos_price, result, remark='',
                              receipt_no='', pos_no='', lpe_rule=None, lpe_item=None,
                              blank_shared=False):
        """blank_shared=True ใช้ตอน log แถวเสริม (rule/item ที่ 2, 3, ... ของ
        แถวทดสอบเดียวกัน) - เว้นคอลัมน์ที่ซ้ำกับแถวแรกไว้ให้ว่าง เหลือแค่
        คอลัมน์ rule/item ที่ต่างกันจริง กันไม่ให้ดูรกซ้ำในรายงาน
        """
        if blank_shared:
            entry = {col: '' for col in self.RESULT_COLUMNS}
        else:
            row = self._get_row(index)
            entry = {
                'promotion_code': row.get('promotion_code', ''),
                'promotion_name': row.get('promotion_name', ''),
                'active_from': row.get('active_from', ''),
                'active_to': row.get('active_to', ''),
                'redemption_limit_per_transaction': row.get('redemption_limit_per_transaction', ''),
                'bucketid': row.get('bucketid', ''),
                'trigger_value': row.get('trigger_value', ''),
                'entity_code': row.get('entity_code', ''),
                'entity_name': row.get('entity_name', ''),
                'barcode_used': row.get('barcode', ''),
                'reward_value': row.get('reward_value', ''),
                'notes': row.get('notes', ''),
                'sheet': row.get('sheet', ''),
                'worksheet': row.get('worksheet', ''),
                'receipt_no': receipt_no,
                'pos_no': pos_no,
                'pos_price': pos_price,
                'result': result,
                'remark': remark,
                'executed_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            }
        for col in self.LPE_RULE_COLUMNS:
            entry[col] = (lpe_rule or {}).get(col, '')
        for col in self.LPE_ITEM_COLUMNS:
            entry[col] = (lpe_item or {}).get(col, '')
        self.log_rows.append(entry)
        return True

    def save_new_price_log(self, output_path=None):
        from openpyxl import Workbook
        from openpyxl.styles import PatternFill, Font
        from openpyxl.formatting.rule import FormulaRule
        from openpyxl.utils import get_column_letter

        columns = self.RESULT_COLUMNS
        header_labels = [self.HEADER_LABELS.get(col, col) for col in columns]
        wb = Workbook()
        results = wb.active
        results.title = 'Results'
        results.append(header_labels)
        for row in self.log_rows:
            results.append([row.get(col, '') for col in columns])

        last_row = len(self.log_rows) + 1
        last_col_letter = get_column_letter(len(columns))
        results.freeze_panes = 'A2'
        results.auto_filter.ref = 'A1:{0}{1}'.format(last_col_letter, last_row)

        header_font = Font(bold=True)
        for cell in results[1]:
            cell.font = header_font

        if last_row >= 2:
            result_col_letter = get_column_letter(columns.index('result') + 1)
            data_range = 'A2:{0}{1}'.format(last_col_letter, last_row)
            green_fill = PatternFill(start_color='C6EFCE', end_color='C6EFCE', fill_type='solid')
            red_fill = PatternFill(start_color='FFC7CE', end_color='FFC7CE', fill_type='solid')
            results.conditional_formatting.add(
                data_range,
                FormulaRule(formula=['${0}2="Pass"'.format(result_col_letter)], fill=green_fill))
            results.conditional_formatting.add(
                data_range,
                FormulaRule(formula=['${0}2="Fail"'.format(result_col_letter)], fill=red_fill))

        for col_index, col_name in enumerate(columns, start=1):
            max_len = len(header_labels[col_index - 1])
            for row in self.log_rows:
                max_len = max(max_len, len(str(row.get(col_name, ''))))
            results.column_dimensions[get_column_letter(col_index)].width = min(max_len + 2, 60)

        summary = wb.create_sheet('Summary')
        summary.append(['Field', 'Value'])
        for cell in summary[1]:
            cell.font = header_font
        summary.append(['worksheet', self.worksheet_name])
        summary.append(['start_row', self.start_row])
        summary.append(['end_row', self.end_row])
        result_col_letter = get_column_letter(columns.index('result') + 1)
        summary.append(['total_tested', '=COUNTA(Results!A2:A1000)'])
        summary.append(['total_pass', '=COUNTIF(Results!{0}:{0},"Pass")'.format(result_col_letter)])
        summary.append(['total_fail', '=COUNTIF(Results!{0}:{0},"Fail")'.format(result_col_letter)])
        summary.append(['pass_rate', '=IF(B5=0,0,B6/B5*100)'])
        summary['B8'].number_format = '0.00"%"'
        summary.append(['executed_at', datetime.now().strftime('%Y-%m-%d %H:%M:%S')])
        summary.column_dimensions['A'].width = 16
        summary.column_dimensions['B'].width = 60

        if not output_path:
            output_path = self._build_log_file_path()
        output_path = os.path.abspath(output_path)
        output_dir = os.path.dirname(output_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)
        wb.save(output_path)
        return output_path

    def _build_log_file_path(self):
        log_dir = self._new_price_config().get('log_dir', '../results')
        log_dir_abs = os.path.abspath(os.path.join(self.library_directory, log_dir))
        safe_worksheet = self._sanitize_filename_part(self.worksheet_name or 'Sheet1')
        filename = 'log_{0}_{1}-{2}_{3}.xlsx'.format(
            safe_worksheet, self.start_row, self.end_row, datetime.now().strftime('%Y%m%d'))
        return os.path.join(log_dir_abs, filename)

    @staticmethod
    def _sanitize_filename_part(text):
        text = re.sub(r'\.xlsx$', '', text, flags=re.IGNORECASE)
        text = re.sub(r'[^0-9A-Za-zก-๏_-]+', '_', text)
        text = text.strip('_')
        if len(text) > 40:
            text = text[:40]
        return text or 'Sheet1'

    def _finish_bill_and_read_result(self, log_index, delay, pos_no):
        """กดปุ่ม "รับพอดี" -> รอ/ยืนยัน popup -> เช็ค M-Stamp popup -> รอ
        database บันทึกบิล -> อ่านราคาสุทธิ (TS_SALE_ITEM) + LPE promotion
        check ย้อนหลัง - ใช้ร่วมกันทั้ง New Price/Free Item
        (process_new_price_row) และ Amount Off (AmountOffRobot) เพราะ
        ขั้นตอนปิดบิล/อ่านผลลัพธ์เหมือนกันทุกอย่าง ต่างกันแค่ตอนก่อนหน้านี้
        (สแกนสินค้ายังไงกว่าจะมาถึงจุดนี้)

        คืนค่า (pos_price, first_rule, first_item) และตั้ง self.last_lpe_combos
        ไว้ให้เรียก log ทีละ combo ต่อได้เหมือนเดิม
        """
        self._log_step(log_index, 'Click receive-exact button')
        self.robot.click_at(*self.get_new_price_coordinate('receive_exact_button'))
        time.sleep(delay)
        self._log_step(log_index, 'Waiting for confirm popup (checking Yes button text)')
        popup_timeout = float(self.get_new_price_setting('popup_timeout_seconds', 10))
        popup_ok = self.wait_for_popup_button(popup_timeout, delay)
        # popup บางครั้งเด้งช้ากว่าปกติ (POS ยุ่งประมวลผลบิลก่อนหน้า) -
        # ก่อนถือว่า Fail จริง ลองคลิกปุ่ม "รับพอดี" ซ้ำแล้วรอใหม่อีกรอบ
        retry_count = int(self.get_new_price_setting('receive_exact_retry_count', 1))
        attempt = 1
        while not popup_ok and attempt <= retry_count:
            attempt += 1
            self._log_step(
                log_index, 'Popup not detected yet - retry {0}/{1}: '
                'click receive-exact button again'.format(attempt, retry_count + 1))
            self.robot.click_at(*self.get_new_price_coordinate('receive_exact_button'))
            time.sleep(delay)
            popup_ok = self.wait_for_popup_button(popup_timeout, delay)
        if not popup_ok:
            raise AssertionError(
                'popup ยืนยันรับพอดี (Confirm) ไม่เด้ง (ลองแล้ว {0} ครั้ง)'.format(
                    retry_count + 1))

        self._log_step(log_index, 'Click Yes to confirm popup')
        self.robot.click_at(*self.get_new_price_coordinate('popup_confirm_yes_button'))
        time.sleep(delay)
        self._handle_mstamp_choice_popup(log_index, delay)
        self._log_step(
            log_index, 'Row {0} done (bill close will be confirmed via database check below)'.format(
                log_index))

        db_wait = float(self.get_new_price_setting('db_price_check_wait_seconds', 10))
        self._log_step(log_index, 'Waiting {0}s for database to record the sale (bill closed)'.format(db_wait))
        time.sleep(db_wait)
        self._log_step(log_index, 'Reading price from database (TS_SALE_ITEM) retroactively')
        pos_price = self.read_price_from_db()
        self._log_step(log_index, 'Price read: {0}'.format(pos_price))
        rule_rows, item_rows = self.read_lpe_promotion_check(
            pos_no, receipt_no=self.last_receipt_no)
        self._log_step(
            log_index, 'LPE item_rows count={0}, product_codes seen={1}'.format(
                len(item_rows), [r.get('PRODUCT_CODE') for r in item_rows]))
        self.last_lpe_combos = self._build_lpe_combos(rule_rows, item_rows)
        first_rule, first_item = self.last_lpe_combos[0]
        self._log_step(
            log_index, 'LPE promotion check: combos={0}, rule_name={1}, sumamt={2}, '
            'item_reware={3}'.format(
                len(self.last_lpe_combos), first_rule.get('rule_name'),
                first_rule.get('sumamt'), first_item.get('item_reware')))
        return pos_price, first_rule, first_item

    # ------------------------------------------------------------------
    # ขั้นตอนเต็มของ POS ต่อ 1 แถว (สั่งงาน CoordinateRobot ตรงๆ เพราะ Robot
    # Framework 3.1.2 ไม่มี IF/ELSE block ให้เขียนเงื่อนไขแบบนี้)
    # ------------------------------------------------------------------
    def process_new_price_row(self, index, helper_indices=None, run_number=None):
        """helper_indices: รายการ index ของแถวอื่น (bucketid tier ต่ำกว่า
        ของ promotion_code เดียวกัน) ที่ต้องสแกนรวมในบิลเดียวกันก่อน ถึงจะ
        เข้าเงื่อนไขส่วนลดของแถว index ที่กำลังทดสอบจริง (มาจาก
        _build_new_price_bill_plans - จับคู่แถวจริงตามตำแหน่ง ไม่ใช่ดึงตัว
        แทนซ้ำๆจาก database) - ราคาที่ตรวจสอบยังเทียบกับ reward_value ของ
        แถว index เดียว ไม่บวกรวมกับ reward_value ของ helper

        run_number: เลขบิลลำดับที่กำลังรันจริง (1, 2, 3, ... ตามจำนวนบิล
        ทั้งหมด) ใช้แสดงใน step log แทน index ดิบ - เพราะ index (แถวใน
        database) อาจถูกทดสอบซ้ำหลายบิล (เช่น bucketid สูงสุดมีแถวเดียว
        แต่ถูกจับคู่กับ helper คนละตัวหลายรอบ) ถ้าโชว์ index ตรงๆ log จะ
        ดูเหมือน "Row 4" ซ้ำกันหลายครั้งจนสับสนว่าเป็นบิลเดียวกันหรือเปล่า
        - ไม่ใส่มาก็ fallback ไปใช้ index เหมือนเดิม (ไม่กระทบของเก่า)
        """
        log_index = run_number if run_number is not None else index
        barcode = ''
        pos_price = ''
        pos_no = self._pos_sql_config().get('pos_no', '')
        self.last_receipt_no = ''
        self.last_lpe_combos = [({}, {})]
        try:
            delay = float(self.get_new_price_setting('step_delay_seconds', 2.0))
            self._log_step(log_index, 'Start row {0}'.format(log_index))

            row_for_day_check = self._get_row(index)
            is_active_today, active_days_th, today_name_th = self.check_promotion_active_today(
                row_for_day_check.get('promotion_code'))
            if not is_active_today:
                remark = (
                    'เล่นเฉพาะวัน {0} (วันนี้ {1}) - ข้ามการทดสอบ (เจอจาก '
                    'LPE_PromotionHeader)'.format(
                        ', '.join(active_days_th) if active_days_th else 'ไม่มีวันที่เปิดเล่นเลย',
                        today_name_th))
                self._log_step(log_index, 'SKIP (N/A): {0}'.format(remark))
                self.log_new_price_result(index, '', '', 'N/A', remark, receipt_no='', pos_no=pos_no)
                return True

            baseline = self.capture_sql_baseline()
            self._log_step(log_index, 'Captured baseline RECEIPT_NO before scan: {0}'.format(baseline))

            for helper_idx in (helper_indices or []):
                helper_row = self._get_row(helper_idx)
                helper_barcode = self._compute_barcode_for_row(helper_row)
                self._log_step(
                    log_index, 'Scanning lower-tier item first (row {0}): {1}'.format(
                        helper_idx, helper_barcode))
                self._scan_barcode_and_check(log_index, helper_barcode, delay)

            barcode = self.compute_new_price_barcode(index)
            self._log_step(log_index, 'Click barcode input field to set focus before typing')
            self._scan_barcode_and_check(log_index, barcode, delay)
            self._log_step(log_index, 'Press numpad + (Add) to go to payment screen')
            self.robot.send_keys('{Add}')
            time.sleep(delay)

            if self.is_new_price_member_segment(
                    index, 'Apply Promotion to All Customers (no card required)'):
                self._log_step(log_index, 'Case A: no member card required')
            elif self.is_new_price_member_segment(index, 'All Members (card required)'):
                self._log_step(log_index, 'Case B: member card required - starting member flow')
                self._run_member_card_flow(log_index, delay)
            else:
                row = self._get_row(index)
                raise AssertionError(
                    'ไม่รองรับ member_segmentation: ' +
                    str(row.get('member_segmentation', '')))

            pos_price, first_rule, first_item = self._finish_bill_and_read_result(
                log_index, delay, pos_no)
            if not self.new_price_matches_reward(index, pos_price, first_item):
                if not first_rule.get('rule_id'):
                    # ไม่มี rule ยิงเข้า TA_PROMOTION_HITRULE เลย (เช็คจาก
                    # RULE_ID ว่างสนิท) - ราคาที่ได้คือราคาปกติ ไม่ใช่แค่
                    # ราคาผิดจากที่คาด แปลว่าโปรไม่เข้าตั้งแต่แรก ให้ remark
                    # ที่ชัดเจนกว่า "ราคาไม่ตรงกัน" เฉยๆ
                    raise AssertionError(
                        'ไม่ได้โปร (ไม่มี rule ยิงเข้า database - pos_price={0}, '
                        'reward_value={1})'.format(
                            pos_price, self._get_row(index).get('reward_value', '')))
                raise AssertionError(
                    'ราคาไม่ตรงกัน (เทียบย้อนหลังจาก database - pos_price={0}, '
                    'reward_value={1})'.format(
                        pos_price, self._get_row(index).get('reward_value', '')))
            if not self.new_price_matches_rule(index, first_rule):
                row = self._get_row(index)
                raise AssertionError(
                    'promotion_code/promotion_name ไม่ตรงกับ RULE_ID/RULE_NAME จาก database '
                    '(คาดหวัง {0}/{1}, ได้ {2}/{3})'.format(
                        row.get('promotion_code'), row.get('promotion_name'),
                        first_rule.get('rule_id'), first_rule.get('rule_name')))
            remark = ''
            for i, (rule_dict, item_dict) in enumerate(self.last_lpe_combos):
                self.log_new_price_result(
                    index, barcode, pos_price, 'Pass', remark, receipt_no=self.last_receipt_no,
                    pos_no=pos_no, lpe_rule=rule_dict, lpe_item=item_dict, blank_shared=(i > 0))
        except AssertionError as exc:
            self._log_step(log_index, 'FAIL: {0}'.format(exc))
            self.log_new_price_result(
                index, barcode, pos_price, 'Fail', str(exc), receipt_no=self.last_receipt_no,
                pos_no=pos_no)
        except Exception as exc:
            self._log_step(log_index, 'FAIL (unexpected): {0}'.format(exc))
            self.log_new_price_result(
                index, barcode, pos_price, 'Fail', 'เกิดข้อผิดพลาดที่ไม่คาดคิด: ' + str(exc),
                receipt_no=self.last_receipt_no, pos_no=pos_no)
        return True

    @staticmethod
    def _log_step(index, message):
        text = 'Row {0}: {1}'.format(index, message)
        logger.info(text)
        logger.console(text)

    def run_new_price_test_suite(self):
        """ไม่เรียก self.sign_off() ในนี้แล้ว - ย้ายไปเรียกแยกเป็น step
        ของตัวเองใน .robot keyword (Run New Price Promotion Test / Run
        Free Item Promotion Test) เพื่อให้เห็นชัดใน .robot ว่ามี Sign Off
        เกิดขึ้นจริง ไม่ซ่อนอยู่ในนี้
        """
        self.load_new_price_rows()
        self.init_new_price_log()
        bill_plans = self._build_new_price_bill_plans()
        log_path = None
        for run_number, plan in enumerate(bill_plans, start=1):
            index = plan['tested_index']
            self.process_new_price_row(
                index, helper_indices=plan['helper_indices'], run_number=run_number)
            # เซฟทับไฟล์เดิมทุกแถว กันข้อมูลหายถ้าเกิดค้าง/พังกลางทาง - ถ้าเซฟ
            # ไม่สำเร็จ (เช่นไฟล์ถูกเปิดอยู่ใน Excel ตอนนั้น) แค่ log คำเตือน
            # ไม่ให้ suite ทั้งชุดพังไปเลย ข้อมูลยังอยู่ใน self.log_rows ครบ
            # เดี๋ยวลองเซฟใหม่รอบถัดไป
            try:
                log_path = self.save_new_price_log(log_path)
            except Exception as exc:
                logger.warn(
                    'Save log failed after run {0} (probably file is open elsewhere): '
                    '{1} - will retry after the next row'.format(run_number, exc))
        try:
            return log_path or self.save_new_price_log()
        except Exception as exc:
            logger.warn('Final save log failed: {0}'.format(exc))
            return log_path

    def sign_off(self):
        """หลังทำครบทุกแถวแล้ว กด Esc กลับไปหน้าเมนู แล้วกดปุ่ม Sign Off

        ไม่ throw error ถ้าล้มเหลว (เช่น sign_off_button ยังไม่ calibrate)
        เพราะเป็นแค่ขั้นตอนปิดท้าย ไม่ควรทำให้ผลทดสอบทุกแถวที่ทำสำเร็จไปแล้ว
        กลายเป็น fail ไปด้วย
        """
        delay = float(self.get_new_price_setting('step_delay_seconds', 2.0))
        try:
            logger.info('Sign off: pressing Esc then clicking Sign Off button')
            self.robot.send_keys('{Esc}')
            time.sleep(delay)
            self.robot.click_at(*self.get_new_price_coordinate('sign_off_button'))
            time.sleep(delay)
            logger.info('Sign off: confirming "Yes" on the sign off popup')
            self.robot.click_at(*self.get_new_price_coordinate('popup_confirm_yes_button'))
            time.sleep(delay)
        except Exception as exc:
            logger.warn('Sign off failed (non-fatal): {0}'.format(exc))

    def _run_member_card_flow(self, index, delay):
        self._log_step(index, 'Click member / use M-Stamp button')
        self.robot.click_at(*self.get_new_price_coordinate('member_button'))
        time.sleep(delay)

        self._log_step(index, 'Fetching member barcode from API')
        member_barcode = self.fetch_member_barcode()
        self._log_step(index, 'Click member barcode input, then type: {0}'.format(member_barcode))
        self.robot.click_at(*self.get_new_price_coordinate('member_barcode_input'))
        time.sleep(delay)
        self.robot.type_text(member_barcode)
        self.robot.press_enter()
        member_welcome_load_wait = float(
            self.get_new_price_setting('member_welcome_load_wait_seconds', 5.0))
        self._log_step(
            index, 'Waiting {0}s for member welcome screen to load'.format(member_welcome_load_wait))
        time.sleep(member_welcome_load_wait)
        self._confirm_member_welcome(index, delay)

    def _is_on_member_welcome_screen(self):
        """เช็คว่ายังอยู่หน้ายินดีต้อนรับสมาชิกไหม โดยดูสีพิกเซลบน header
        (เขียวเข้ม) แทนการอ่านข้อความ เพราะแอปนี้วาดเองทั้งหมด อ่าน text
        ผ่าน Windows API ไม่ได้เลยสักจุด (ปุ่ม, ราคา, header ว่างหมด)
        """
        header_x, header_y = self.get_new_price_coordinate('member_welcome_header')
        red, green, blue = self.robot.get_pixel_color(header_x, header_y)
        # header เป็นแถบเขียวเข้ม: เขียวเด่นกว่าแดง/น้ำเงินชัดเจน
        is_green = green > 80 and green > red + 30 and green > blue + 30
        return is_green, (red, green, blue)

    def _confirm_member_welcome(self, index, delay):
        confirm_x, confirm_y = self.get_new_price_coordinate('member_welcome_confirm_button')

        try:
            self.get_new_price_coordinate('member_welcome_header')
        except AssertionError:
            self._log_step(index, 'member_welcome_header not calibrated - clicking confirm once without verifying')
            self.robot.click_at(confirm_x, confirm_y)
            time.sleep(delay)
            return

        timeout = float(self.get_new_price_setting('member_confirm_retry_timeout_seconds', 60))
        deadline = time.time() + timeout
        attempt = 0
        rgb = (0, 0, 0)
        while time.time() < deadline:
            attempt += 1
            self._log_step(
                index, 'Click confirm (member welcome screen), attempt {0}'.format(attempt))
            self.robot.click_at(confirm_x, confirm_y)
            time.sleep(delay * 1.5)
            still_here, rgb = self._is_on_member_welcome_screen()
            if not still_here:
                self._log_step(
                    index, 'Left member welcome screen (header rgb={0})'.format(rgb))
                return
            self._log_step(
                index, 'Still on member welcome screen (header rgb={0}), will retry'.format(rgb))
        self._log_step(
            index,
            'Warning: confirm retried until timeout ({0}s, {1} attempts), still looks like member '
            'welcome screen (header rgb={2}) - continuing without failing this row'.format(
                timeout, attempt, rgb))
