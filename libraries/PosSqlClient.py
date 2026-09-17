# -*- coding: utf-8 -*-
"""ฟังก์ชันหลักที่คุยกับ SQL Server (POSG2) โดยตรง - อ่านราคาขายจริงจาก
TS_SALE_ITEM และดึงรายละเอียดโปรโมชันที่ยิงจริงจากสคริปต์ LPE
(lpe_promotion_check.sql) แยกออกมาจาก NewPriceRobot.py เพราะเป็นส่วน
"ติดต่อ database" ล้วนๆ ไม่เกี่ยวกับการคลิก/พิมพ์บนหน้าจอ POS เลย - ใช้
เป็น mixin (NewPriceRobot สืบทอดคลาสนี้ต่อ) เพื่อให้ยังใช้
self.credentials/self.library_directory/self.get_new_price_setting(...)
ของ NewPriceRobot ได้ตามปกติ
"""
import os
import time
from datetime import datetime


class PosSqlClient(object):
    # เรียงตาม Python's datetime.weekday() (0=จันทร์ ... 6=อาทิตย์) ให้ index
    # ตรงกันเป๊ะระหว่าง 2 list นี้
    _WEEKDAY_FG_COLUMNS = ['MON_FG', 'TUE_FG', 'WED_FG', 'THU_FG', 'FRI_FG', 'SAT_FG', 'SUN_FG']
    _WEEKDAY_NAMES_TH = ['จันทร์', 'อังคาร', 'พุธ', 'พฤหัสบดี', 'ศุกร์', 'เสาร์', 'อาทิตย์']

    def check_promotion_active_today(self, promotion_code):
        """เช็คว่าโปรนี้ (MMBR_PROM_ID = promotion_code) ตั้งให้เล่นวันนี้
        ไหม จาก LPE_PromotionHeader (SUN_FG..SAT_FG, 0=ไม่เล่น, 1=เล่น) - ใช้
        วันที่ของเครื่อง POS ที่รันสคริปต์นี้อยู่ (datetime.now() - สคริปต์
        นี้รันอยู่บนเครื่อง POS โดยตรงผ่าน ctypes อยู่แล้ว)

        ถ้าไม่พบแถว MMBR_PROM_ID นี้เลยใน LPE_PromotionHeader ถือว่าโปรนี้
        ไม่จำกัดวัน (ไม่ block การทดสอบ) เพราะโปรบางตัวอาจไม่มีแถวในตารางนี้

        คืนค่า (is_active_today: bool, active_day_names_th: list, today_name_th: str)
        """
        conn = self._get_sql_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                'SELECT SUN_FG, MON_FG, TUE_FG, WED_FG, THU_FG, FRI_FG, SAT_FG '
                'FROM [LPE_PROM].[dbo].[LPE_PromotionHeader] WHERE MMBR_PROM_ID = ?',
                promotion_code)
            row = cur.fetchone()
            if not row:
                return True, [], ''
            columns = [c[0] for c in cur.description]
            data = dict(zip(columns, row))
            flags = [data.get(col) for col in self._WEEKDAY_FG_COLUMNS]
            weekday_index = datetime.now().weekday()
            active_days_th = [
                name for name, flag in zip(self._WEEKDAY_NAMES_TH, flags)
                if str(flag) == '1']
            is_active_today = str(flags[weekday_index]) == '1'
            return is_active_today, active_days_th, self._WEEKDAY_NAMES_TH[weekday_index]
        finally:
            conn.close()
    def _pos_sql_config(self):
        cfg = self.credentials.get('pos_sql')
        if not cfg:
            raise AssertionError('pos_sql ยังไม่ได้ตั้งค่าใน login_credentials.json')
        return cfg

    def _get_sql_connection(self):
        import pyodbc
        cfg = self._pos_sql_config()
        port = cfg.get('port', 1433)
        server = '{0},{1}'.format(cfg.get('server'), port)
        conn_str = 'DRIVER={{SQL Server}};SERVER={0};DATABASE={1};UID={2};PWD={3}'.format(
            server, cfg.get('database'), cfg.get('username'), cfg.get('password'))
        return pyodbc.connect(conn_str, timeout=5)

    def capture_sql_baseline(self):
        """จดจำเลข RECEIPT_NO ล่าสุดของเครื่องนี้ ก่อนสแกนบาร์โค้ดแถวนี้

        ใช้หาว่ารายการที่ปรากฏใหม่ใน TS_SALE_ITEM หลังจากนี้คือรายการของ
        แถวที่กำลังทดสอบอยู่ (ไม่ใช่รายการเก่าจากแถวก่อนหน้า)
        """
        pos_no = self._pos_sql_config().get('pos_no')
        conn = self._get_sql_connection()
        try:
            cur = conn.cursor()
            cur.execute('SELECT MAX(RECEIPT_NO) FROM TS_SALE_ITEM WHERE POS_NO = ?', pos_no)
            row = cur.fetchone()
            self._sql_baseline_receipt_no = row[0] if row else None
        finally:
            conn.close()
        return self._sql_baseline_receipt_no

    def read_price_from_db(self, timeout=None, interval=1.0):
        if timeout is None:
            timeout = float(self.get_new_price_setting('db_price_check_timeout_seconds', 60))
        pos_no = self._pos_sql_config().get('pos_no')
        if pos_no is None:
            raise AssertionError('pos_sql.pos_no ยังไม่ได้ตั้งค่าใน login_credentials.json')
        baseline = getattr(self, '_sql_baseline_receipt_no', None)
        deadline = time.time() + float(timeout)
        while time.time() < deadline:
            conn = self._get_sql_connection()
            try:
                cur = conn.cursor()
                cur.execute(
                    'SELECT MAX(RECEIPT_NO) FROM TS_SALE_ITEM WHERE POS_NO = ?', pos_no)
                row = cur.fetchone()
                receipt_no = row[0] if row else None
                if receipt_no is not None and receipt_no != baseline:
                    cur.execute(
                        'SELECT SUM(TOTAL_AMT) FROM TS_SALE_ITEM '
                        'WHERE RECEIPT_NO = ? AND POS_NO = ?', receipt_no, pos_no)
                    total_row = cur.fetchone()
                    total = total_row[0] if total_row else None
                    if total is not None:
                        self.last_receipt_no = receipt_no
                        return float(total)
            finally:
                conn.close()
            time.sleep(float(interval))
        raise AssertionError(
            'ไม่พบข้อมูลการขายใหม่ใน TS_SALE_ITEM (POS_NO={0}, baseline RECEIPT_NO={1})'.format(
                pos_no, baseline))

    def get_sale_price_from_ms_price_sale(self, product_code):
        """ราคาขายจริงปัจจุบันของสินค้า (ก่อนหักโปร Amount Off) จาก
        MS_PRICE_SALE - ใช้ประมาณยอดสะสมล่วงหน้าระหว่างสแกน bucketid=1
        (ยังไม่ใช่ราคาสุทธิหลังหักส่วนลดจริง อันนั้นต้องเช็คด้วย OCR ที่
        หน้าชำระเงินอีกที เพราะราคาจริงอาจต่างจากตารางนี้)
        """
        store_code = self.credentials.get('store_code', '')
        conn = self._get_sql_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                'SELECT TOP 1 SALE_PRICE FROM MS_PRICE_SALE '
                'WHERE PRODUCT_CODE = ? AND STORE_ID = ? AND PROMOTION_TYPE_NO = 0 '
                'AND (EFFECTIVE_DATETIME IS NULL OR EFFECTIVE_DATETIME <= GETDATE()) '
                'AND (EXPIRE_DATETIME IS NULL OR EXPIRE_DATETIME >= GETDATE()) '
                'ORDER BY EFFECTIVE_DATETIME DESC',
                product_code, store_code)
            row = cur.fetchone()
            if not row or row[0] is None:
                raise AssertionError(
                    'ไม่พบราคาใน MS_PRICE_SALE (PRODUCT_CODE={0}, STORE_ID={1})'.format(
                        product_code, store_code))
            return float(row[0])
        finally:
            conn.close()

    @staticmethod
    def _fetch_all_as_dicts(cur):
        """แปลงผล cursor เป็น list ของ dict โดยกันชื่อคอลัมน์ซ้ำ (script LPE
        มีคอลัมน์ชื่อ UNIT ซ้ำกัน 2 ที) ด้วยการเติม _1, _2 ต่อท้ายตัวที่ซ้ำ
        """
        if not cur.description:
            return []
        raw_columns = [c[0] for c in cur.description]
        seen = {}
        columns = []
        for col in raw_columns:
            if col in seen:
                seen[col] += 1
                columns.append('{0}_{1}'.format(col, seen[col]))
            else:
                seen[col] = 0
                columns.append(col)
        return [dict(zip(columns, r)) for r in cur.fetchall()]

    def _run_lpe_promotion_check_once(self, pos_no, receipt_no=None):
        """รัน SQL script เต็มรูปแบบ (LPE) ที่ทีมให้มา เพื่อดึงรายละเอียด
        โปรโมชัน (grid1: RCNO,NO,RULE_ID,PROM_DESC,RULE_NAME,UNIT,UNITRU,
        PRICE,UNIT,SUMAMT,UNITAMT,TYPE,MMBR_ID,RWRD_MMBR) และรายการสินค้า
        (grid2: RECEIPT,POS,PRODUCT_CODE,PRODUCT_NAME,PRICE,QTY,TOTAL_AMT,
        REWARE,QTY_S,UNIT_T,TARGETS) ของบิลล่าสุดที่ POS_NO นี้ทำ

        สคริปต์นี้เลือกบิลจาก MAX(COMMON_TRN_NO) ของ POS_NO เฉยๆ (ไม่กรอง
        ตาม receipt_no ที่เราต้องการจริง) - ถ้าบิลปัจจุบันไม่มี rule ยิงเข้า
        TA_PROMOTION_HITRULE เลย (เช่นกรณีราคาไม่ตรง/โปรไม่ขึ้นจริงบน POS)
        สคริปต์จะคืนค่าของบิลก่อนหน้าที่ยิง rule ล่าสุดมาแทน ทำให้ข้อมูล
        rule/item ในแถว Fail ซ้ำกับแถว Pass ก่อนหน้า (ข้อมูลเก่าปนเข้ามา) -
        ถ้าระบุ receipt_no มา จะเทียบกับ RCNO (rule) / RECEIPT (item สรุป)
        แล้วตัดข้อมูลที่ไม่ตรง receipt ปัจจุบันออก ป้องกันไม่ให้ข้อมูลเก่า
        หลุดเข้าไปใน log ของแถวที่ไม่ได้เกี่ยวข้องกัน

        คืนค่า (rule_rows, item_rows) - list ของ dict ต่อ result set
        """
        sql_path = os.path.join(self.library_directory, 'lpe_promotion_check.sql')
        with open(sql_path, 'r', encoding='utf-8-sig') as f:
            script = f.read()
        script = script.replace('__POS_NO__', str(int(pos_no)))

        conn = self._get_sql_connection()
        try:
            cur = conn.cursor()
            cur.execute(script)
            # เดินดูทุก result set ที่ driver ส่งมา แล้วแยกด้วยชื่อคอลัมน์จริง
            # (ไม่เดาลำดับ) เผื่อมี result set แถมจากคำสั่งอื่นในสคริปต์ปนมา
            rule_rows, item_rows = [], []
            has_more = True
            while has_more:
                if cur.description:
                    col_names = set(c[0] for c in cur.description)
                    rows = self._fetch_all_as_dicts(cur)
                    if 'RCNO' in col_names and rows:
                        rule_rows = rows
                    elif 'RECEIPT' in col_names and rows:
                        item_rows = rows
                has_more = cur.nextset()

            if receipt_no not in (None, ''):
                expected = str(receipt_no).strip()
                rule_rows = [r for r in rule_rows if str(r.get('RCNO', '')).strip() == expected]
                summary_matches = any(
                    str(r.get('RECEIPT', '')).strip() == expected
                    for r in item_rows if r.get('RECEIPT'))
                if not summary_matches:
                    item_rows = []

            return rule_rows, item_rows
        finally:
            conn.close()

    def read_lpe_promotion_check(self, pos_no, receipt_no=None, timeout=None, interval=2.0):
        """เหมือน _run_lpe_promotion_check_once แต่ลอง poll ซ้ำจนกว่าจะเจอ
        ข้อมูล เพราะ TA_PROMOTION_HITRULE/TA_PROMOTION_ITEM อาจบันทึกช้ากว่า
        TS_SALE_ITEM - ถ้ายังไม่เจอจน timeout จะคืนค่าว่าง (ไม่ throw error
        เพราะข้อมูลนี้เป็นแค่ส่วนเสริม ไม่ใช่ตัวตัดสิน Pass/Fail หลัก)

        ถ้าระบุ receipt_no จะกรองผลให้ตรงกับบิลปัจจุบันเท่านั้น (กันข้อมูล
        เก่าจากบิลก่อนหน้าหลุดเข้ามาเวลาบิลนี้ไม่มี rule ยิงจริง)
        """
        if timeout is None:
            timeout = float(self.get_new_price_setting('lpe_check_timeout_seconds', 90))
        deadline = time.time() + float(timeout)
        rule_rows, item_rows = [], []
        while time.time() < deadline:
            rule_rows, item_rows = self._run_lpe_promotion_check_once(pos_no, receipt_no=receipt_no)
            if rule_rows:
                return rule_rows, item_rows
            time.sleep(float(interval))
        return rule_rows, item_rows

    @staticmethod
    def _map_lpe_rule_row(row):
        if not row:
            return {}
        return {
            'rule_id': row.get('RULE_ID', ''),
            'prom_desc': row.get('PROM_DESC', ''),
            'rule_name': row.get('RULE_NAME', ''),
            'unit': row.get('UNIT', ''),
            'unitru': row.get('UNITRU', ''),
            'price': row.get('PRICE', ''),
            'unit2': row.get('UNIT_1', ''),
            'sumamt': row.get('SUMAMT', ''),
            'unitamt': row.get('UNITAMT', ''),
            'type': row.get('TYPE', ''),
            'mmbr_id': row.get('MMBR_ID', ''),
            'rwrd_mmbr': row.get('RWRD_MMBR', ''),
        }

    @staticmethod
    def _map_lpe_item_row(rows):
        """@ITEM query คืนมา 2 แถวต่อบิล (UNION ALL): แถวสรุปมี RECEIPT/POS
        จริงแต่ PRODUCT_CODE/PRICE/QTY ว่าง ส่วนแถวรายละเอียดสินค้ามี
        PRODUCT_CODE/PRICE/QTY จริงแต่ RECEIPT/POS ว่าง - รวมค่าที่ไม่ว่าง
        จากทุกแถวเข้าด้วยกันเป็นชุดเดียว (ไม่เก็บ RECEIPT/POS ต่อแล้ว เพราะมี
        receipt_no/pos_no จากที่อื่นซ้ำอยู่แล้ว)
        """
        if not rows:
            return {}
        if isinstance(rows, dict):
            rows = [rows]
        field_map = {
            'product_code': 'PRODUCT_CODE', 'product_name': 'PRODUCT_NAME',
            'item_price': 'PRICE', 'item_qty': 'QTY', 'item_total_amt': 'TOTAL_AMT',
            'item_reware': 'REWARE', 'qty_s': 'QTY_S', 'unit_t': 'UNIT_T',
            'targets': 'TARGETS',
        }
        merged = {key: '' for key in field_map}
        # เดินย้อนหลัง (แถวรายละเอียดสินค้าก่อน แถวสรุปทีหลัง) เพราะแถวสรุป
        # มี PRODUCT_CODE เป็นตัวนับ (ไม่ใช่โค้ดจริง) - ถ้าเดินแบบปกติค่านับ
        # นี้จะไปเติมช่องก่อนโค้ดสินค้าจริงจากแถวรายละเอียด
        for row in reversed(rows):
            for out_key, sql_col in field_map.items():
                value = row.get(sql_col, '')
                if value not in (None, '') and merged[out_key] in ('', None):
                    merged[out_key] = value
        return merged

    @classmethod
    def _build_lpe_combos(cls, rule_rows, item_rows):
        """สร้างชุด (rule_dict, item_dict) หนึ่งชุดต่อ 1 rule/สินค้า - ปกติมี
        แค่ 1 ชุด (1 บิล = 1 สินค้า) แต่ถ้าเจอหลาย rule หรือหลายสินค้าในบิล
        เดียวกันจริงๆ (ผิดคาด) จะคืนมาหลายชุด ให้ log ออกมาเป็นหลายแถวแทน
        การรวมทับกันจนข้อมูลหาย
        """
        rule_dicts = [cls._map_lpe_rule_row(r) for r in rule_rows] if rule_rows else [{}]

        summary = None
        details = []
        for r in (item_rows or []):
            if r.get('RECEIPT'):
                summary = r
            else:
                details.append(r)
        if not details and item_rows:
            details = list(item_rows)

        item_dicts = []
        for detail in details:
            # _map_lpe_item_row เดินย้อนหลัง (reversed) ต้องเอา detail ไว้
            # ท้ายลิสต์ ให้มันถูกประมวลผลก่อน summary (กัน summary เอาค่า
            # นับไปเติมช่อง product_code ก่อนค่าจริงจาก detail)
            combined = [summary, detail] if summary else [detail]
            item_dicts.append(cls._map_lpe_item_row(combined))
        if not item_dicts:
            item_dicts = [{}]

        combo_count = max(len(rule_dicts), len(item_dicts))
        combos = []
        for i in range(combo_count):
            rule_dict = rule_dicts[i] if i < len(rule_dicts) else rule_dicts[-1]
            item_dict = item_dicts[i] if i < len(item_dicts) else item_dicts[-1]
            combos.append((rule_dict, item_dict))
        return combos
