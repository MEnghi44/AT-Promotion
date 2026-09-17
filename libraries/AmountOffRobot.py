# -*- coding: utf-8 -*-
"""ทดสอบโปรโมชัน "Amount Off" (ซื้อสินค้า bucketid=1 ให้ครบยอดสะสมตาม
trigger_value เพื่อปลดล็อกสินค้า bucketid=2 ราคาพิเศษ)

ต่างจาก New Price/Free Item เพราะ query database เฉยๆ ไม่พอ - บิลต้องปิด
ก่อนถึงจะรู้ราคาสุทธิจริงจาก TS_SALE_ITEM แต่บิลยังปิดไม่ได้จนกว่าจะสแกน
สินค้า bucketid=1 ครบยอด (ซึ่งต้องรู้ก่อนว่าสแกนพอหรือยัง) จึงใช้วิธี:

1. ประมาณยอดสะสมล่วงหน้าจาก MS_PRICE_SALE ระหว่างสแกน bucketid=1 ทีละชิ้น
   (วนกลับไปสแกนแถวเดิมซ้ำได้ถ้ามี bucketid=1 แถวเดียวหรือสแกนจนหมด list
   แล้วยังไม่ครบยอด)
2. เมื่อประมาณว่าครบแล้ว ไปหน้าชำระเงิน (หน้า B) เช็คของจริงด้วย OCR (อ่าน
   "ยอดที่ต้องชำระ") - ถ้าราคาจริงต่างจาก MS_PRICE_SALE จนส่วนลดยังไม่เข้า
   กด Esc กลับไปสแกนเพิ่มอีก 1 ชิ้น (สินค้าที่สแกนไปแล้วยังอยู่ครบในบิล)
3. เมื่อ OCR ยืนยันว่าส่วนลดเข้าแล้วจริง จึงสแกนสินค้า bucketid=2 (ของ
   ปลดล็อก) แล้วปิดบิลตาม flow เดิม (รับพอดี/ยืนยัน popup/M-Stamp) ใช้
   _finish_bill_and_read_result ที่สืบทอดมาจาก NewPriceRobot
"""
import sys
import os
import time
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from NewPriceRobot import NewPriceRobot
from PriceOcr import PriceOcr


class AmountOffRobot(NewPriceRobot, PriceOcr):
    ROBOT_LIBRARY_SCOPE = 'GLOBAL'

    # ------------------------------------------------------------------
    # จัดกลุ่มแถวที่โหลดมาเป็นบิลที่ต้องทดสอบ
    # ------------------------------------------------------------------
    def _build_amount_off_plans(self):
        """จัดกลุ่ม self.rows ตาม promotion_code แล้วแยกตาม bucketid:
        bucketid=1 คือสินค้าที่ต้องซื้อสะสมให้ครบยอด (มีได้หลายแถว),
        bucketid=2 คือสินค้าที่ปลดล็อก/ได้ราคาพิเศษ (ปกติแถวเดียว แต่ถ้ามี
        หลายแถวจริง ทดสอบทีละแถวเป็นคนละบิล ใช้ bucketid=1 pool เดียวกันซ้ำ
        ได้ เพราะเป็นแค่ตัวช่วยสแกนให้ครบยอด ไม่ใช่ตัวที่ถูกทดสอบ)

        คืนค่า list ของ dict {'promotion_code', 'bucket1_rows', 'bucket2_row'}
        """
        promo_groups = {}
        promo_order = []
        for row in self.rows:
            promo_code = row.get('promotion_code')
            bucket_raw = row.get('bucketid')
            try:
                bucketid = int(float(bucket_raw)) if bucket_raw not in (None, '') else 1
            except ValueError:
                bucketid = 1
            if promo_code not in promo_groups:
                promo_groups[promo_code] = {}
                promo_order.append(promo_code)
            promo_groups[promo_code].setdefault(bucketid, []).append(row)

        plans = []
        for promo_code in promo_order:
            tiers = promo_groups[promo_code]
            bucket1_rows = tiers.get(1, [])
            bucket2_rows = tiers.get(2, [])
            if not bucket1_rows or not bucket2_rows:
                raise AssertionError(
                    'promotion_code {0} ไม่มีครบทั้ง bucketid=1 และ bucketid=2'.format(promo_code))
            for bucket2_row in bucket2_rows:
                plans.append({
                    'promotion_code': promo_code,
                    'bucket1_rows': bucket1_rows,
                    'bucket2_row': bucket2_row,
                })
        return plans

    @staticmethod
    def _trigger_value_of(row):
        trigger_raw = row.get('trigger_value')
        try:
            return float(trigger_raw) if trigger_raw not in (None, '') else 0.0
        except ValueError:
            return 0.0

    # ------------------------------------------------------------------
    # ขั้นตอนสแกนสะสมยอดจนกว่าจะครบ (ใช้ MS_PRICE_SALE ประมาณ + OCR ยืนยัน)
    # ------------------------------------------------------------------
    def _scan_until_threshold(self, log_index, bucket1_rows, trigger_value, delay):
        total_estimated = 0.0
        i = 0
        max_attempts = int(self.get_new_price_setting('amount_off_max_scan_attempts', 30))
        attempts = 0
        while True:
            attempts += 1
            if attempts > max_attempts:
                raise AssertionError(
                    'สแกนสินค้าครบ {0} ครั้งแล้วยังไม่ถึงยอดตามเงื่อนไข '
                    '(total_estimated={1}, trigger_value={2})'.format(
                        max_attempts, total_estimated, trigger_value))
            row = bucket1_rows[i % len(bucket1_rows)]
            i += 1
            barcode = self._compute_barcode_for_row(row)
            self._log_step(
                log_index, 'Scan spend item (attempt {0}/{1}): {2}'.format(
                    attempts, max_attempts, barcode))
            self._scan_barcode_and_check(log_index, barcode, delay)

            sale_price = self.get_sale_price_from_ms_price_sale(row.get('entity_code'))
            total_estimated += sale_price
            self._log_step(
                log_index, 'Accumulated estimated spend: {0} (trigger_value={1})'.format(
                    total_estimated, trigger_value))

            if total_estimated < trigger_value:
                continue

            self._log_step(
                log_index, 'Estimated spend reached threshold - checking payment screen via OCR')
            self.robot.click_at(*self.get_new_price_coordinate('go_to_payment_button'))
            time.sleep(delay)
            ocr_amount_due = self.read_amount_due_from_screen()
            self._log_step(log_index, 'OCR amount due read: {0}'.format(ocr_amount_due))

            not_applied_yet = ocr_amount_due >= total_estimated - 0.005
            self.robot.send_keys('{Esc}')
            time.sleep(delay)
            if not_applied_yet:
                self._log_step(
                    log_index, 'Discount not applied yet (ocr={0}, estimated={1}) - back to '
                    'scan more'.format(ocr_amount_due, total_estimated))
                continue
            self._log_step(
                log_index, 'Discount confirmed via OCR (ocr={0} < estimated={1})'.format(
                    ocr_amount_due, total_estimated))
            return total_estimated

    # ------------------------------------------------------------------
    # เช็คผลลัพธ์
    # ------------------------------------------------------------------
    def amount_off_matches_reward(self, bucket2_row, first_item):
        """reward_value ของแถว bucketid=2 คือราคาที่สินค้านั้นควรถูกคิดเงิน
        จริงหลังโปรเข้า (ราคาพิเศษ/ของแถม) - เทียบกับ item_total_amt (ยอด
        เงินสุทธิของสินค้าตัวนั้นตัวเดียวจาก LPE breakdown) ไม่ใช่ pos_price
        รวมทั้งบิล เพราะบิลนี้มีสินค้า bucketid=1 (ตัวช่วยสแกน) ปนอยู่ด้วย
        """
        try:
            reward_value = float(str(bucket2_row.get('reward_value', '')).replace(',', ''))
        except (TypeError, ValueError):
            return False
        try:
            actual_amount = float(str((first_item or {}).get('item_total_amt', '')).strip())
        except (TypeError, ValueError):
            return False
        return abs(reward_value - actual_amount) < 0.01

    def _amount_off_matches_rule(self, bucket2_row, rule):
        expected_code = str(bucket2_row.get('promotion_code', '')).strip()
        actual_code = str((rule or {}).get('rule_id', '')).strip()
        if expected_code != actual_code:
            return False
        expected_name = str(bucket2_row.get('promotion_name', '')).strip()
        actual_name = str((rule or {}).get('rule_name', '')).strip()
        if not expected_name or not actual_name:
            return False
        return actual_name in expected_name or expected_name in actual_name

    # ------------------------------------------------------------------
    # บันทึกผลทดสอบ (bucket2_row เป็น dict ตรงๆ ไม่ใช่ index ใน self.rows
    # เพราะ 1 บิลของ Amount Off ผูกกับ bucket2_row เดียว ไม่ใช่ index เดียว
    # เหมือน New Price/Free Item)
    # ------------------------------------------------------------------
    def _log_amount_off_result(self, bucket2_row, pos_price, result, remark, receipt_no='',
                                pos_no='', lpe_rule=None, lpe_item=None, blank_shared=False):
        if blank_shared:
            entry = {col: '' for col in self.RESULT_COLUMNS}
        else:
            entry = {
                'promotion_code': bucket2_row.get('promotion_code', ''),
                'promotion_name': bucket2_row.get('promotion_name', ''),
                'active_from': bucket2_row.get('active_from', ''),
                'active_to': bucket2_row.get('active_to', ''),
                'redemption_limit_per_transaction': bucket2_row.get(
                    'redemption_limit_per_transaction', ''),
                'bucketid': bucket2_row.get('bucketid', ''),
                'trigger_value': bucket2_row.get('trigger_value', ''),
                'entity_code': bucket2_row.get('entity_code', ''),
                'entity_name': bucket2_row.get('entity_name', ''),
                'barcode_used': bucket2_row.get('barcode', ''),
                'reward_value': bucket2_row.get('reward_value', ''),
                'notes': bucket2_row.get('notes', ''),
                'sheet': bucket2_row.get('sheet', ''),
                'worksheet': bucket2_row.get('worksheet', ''),
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

    # ------------------------------------------------------------------
    # ขั้นตอนเต็มต่อ 1 บิล
    # ------------------------------------------------------------------
    def process_amount_off_bill(self, plan, run_number=None):
        promo_code = plan['promotion_code']
        bucket1_rows = plan['bucket1_rows']
        bucket2_row = plan['bucket2_row']
        log_index = run_number if run_number is not None else promo_code
        pos_price = ''
        pos_no = self._pos_sql_config().get('pos_no', '')
        self.last_receipt_no = ''
        self.last_lpe_combos = [({}, {})]
        try:
            delay = float(self.get_new_price_setting('step_delay_seconds', 2.0))
            trigger_value = self._trigger_value_of(bucket1_rows[0])
            self._log_step(
                log_index, 'Start promotion_code {0} (trigger_value={1}, bucket1 rows={2})'.format(
                    promo_code, trigger_value, len(bucket1_rows)))

            baseline = self.capture_sql_baseline()
            self._log_step(log_index, 'Captured baseline RECEIPT_NO before scan: {0}'.format(baseline))

            self._scan_until_threshold(log_index, bucket1_rows, trigger_value, delay)

            bucket2_barcode = self._compute_barcode_for_row(bucket2_row)
            self._log_step(log_index, 'Scanning bucketid=2 reward item: {0}'.format(bucket2_barcode))
            self._scan_barcode_and_check(log_index, bucket2_barcode, delay)
            self._log_step(log_index, 'Press numpad + (Add) to go to payment screen')
            self.robot.send_keys('{Add}')
            time.sleep(delay)

            member_segmentation = bucket2_row.get('member_segmentation', '')
            if self._normalize_segment_text(member_segmentation) == self._normalize_segment_text(
                    'Apply Promotion to All Customers (no card required)'):
                self._log_step(log_index, 'Case A: no member card required')
            elif self._normalize_segment_text(member_segmentation) == self._normalize_segment_text(
                    'All Members (card required)'):
                self._log_step(log_index, 'Case B: member card required - starting member flow')
                self._run_member_card_flow(log_index, delay)
            else:
                raise AssertionError(
                    'ไม่รองรับ member_segmentation: ' + str(member_segmentation))

            pos_price, first_rule, first_item = self._finish_bill_and_read_result(
                log_index, delay, pos_no)

            if not self.amount_off_matches_reward(bucket2_row, first_item):
                if not first_rule.get('rule_id'):
                    raise AssertionError(
                        'ไม่ได้โปร (ไม่มี rule ยิงเข้า database - pos_price={0}, '
                        'reward_value={1})'.format(pos_price, bucket2_row.get('reward_value', '')))
                raise AssertionError(
                    'ราคาไม่ตรงกัน (เทียบย้อนหลังจาก database - pos_price={0}, reward_value={1}, '
                    'item_total_amt={2})'.format(
                        pos_price, bucket2_row.get('reward_value', ''),
                        first_item.get('item_total_amt')))
            if not self._amount_off_matches_rule(bucket2_row, first_rule):
                raise AssertionError(
                    'promotion_code/promotion_name ไม่ตรงกับ RULE_ID/RULE_NAME จาก database '
                    '(คาดหวัง {0}/{1}, ได้ {2}/{3})'.format(
                        bucket2_row.get('promotion_code'), bucket2_row.get('promotion_name'),
                        first_rule.get('rule_id'), first_rule.get('rule_name')))

            remark = ''
            for i, (rule_dict, item_dict) in enumerate(self.last_lpe_combos):
                self._log_amount_off_result(
                    bucket2_row, pos_price, 'Pass', remark, receipt_no=self.last_receipt_no,
                    pos_no=pos_no, lpe_rule=rule_dict, lpe_item=item_dict, blank_shared=(i > 0))
        except AssertionError as exc:
            self._log_step(log_index, 'FAIL: {0}'.format(exc))
            self._log_amount_off_result(
                bucket2_row, pos_price, 'Fail', str(exc), receipt_no=self.last_receipt_no,
                pos_no=pos_no)
        except Exception as exc:
            self._log_step(log_index, 'FAIL (unexpected): {0}'.format(exc))
            self._log_amount_off_result(
                bucket2_row, pos_price, 'Fail', 'เกิดข้อผิดพลาดที่ไม่คาดคิด: ' + str(exc),
                receipt_no=self.last_receipt_no, pos_no=pos_no)
        return True

    def run_amount_off_test_suite(self):
        self.load_new_price_rows()
        self.init_new_price_log()
        plans = self._build_amount_off_plans()
        log_path = None
        for run_number, plan in enumerate(plans, start=1):
            self.process_amount_off_bill(plan, run_number=run_number)
            try:
                log_path = self.save_new_price_log(log_path)
            except Exception as exc:
                from robot.api import logger
                logger.warn(
                    'Save log failed after run {0} (probably file is open elsewhere): '
                    '{1} - will retry after the next row'.format(run_number, exc))
        try:
            return log_path or self.save_new_price_log()
        except Exception as exc:
            from robot.api import logger
            logger.warn('Final save log failed: {0}'.format(exc))
            return log_path
