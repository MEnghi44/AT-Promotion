import sqlite3
from robot.api.deco import keyword, library


@library
class db_keywords:

    @keyword
    def get_promotion_rows(
        self, db_path, reward_type, active_from, sheet=None,
        bucketid=None, trigger_type=None, start_row=None, end_row=None,
    ):
        """start_row/end_row are 1-indexed positions within the filtered result set,
        e.g. start_row=2, end_row=20 selects the 2nd through 20th matching rows.

        bucketid/trigger_type: promotion_data มีหลายแถวย่อยต่อ promotion_code แยกตาม bucketid
        และ trigger_type บอกว่า trigger_value ตีความแบบไหน (Quantity=จำนวนชิ้น,
        ItemSpend/Ticket Spend/Tender Spend=จำนวนเงิน, Member Account=แค่เช็คสมาชิก)

        bucketid ที่เป็น "สินค้าจริง" (มีบาร์โค้ด) ไม่คงที่ที่ 1 เสมอไป — แต่ละ promotion_code
        เลือกใช้ bucketid ไม่เหมือนกัน (พบจริง: promo หนึ่งใช้ bucketid=1, อีกโปรใช้ bucketid=2
        เป็นสินค้าหลักก็มี) จึงกรองด้วย "barcode ไม่ว่างเปล่า" เสมอ แทนที่จะยึด bucketid ตายตัว
        ถ้าอยากจำกัด bucketid เฉพาะเจาะจงก็ยังส่ง bucketid= เข้ามาได้ตามปกติ
        """
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        query = (
            "SELECT promotion_code, promotion_name, entity_code, entity_name, "
            "barcode, member_segmentation, reward_value, trigger_value, bucketid, trigger_type "
            "FROM promotion_data WHERE reward_type = ? AND active_from = ? "
            "AND barcode IS NOT NULL AND barcode != ''"
        )
        params = [reward_type, active_from]
        if sheet:
            # sheet รับได้ทั้งค่าเดียว (str) หรือหลายค่า (list) — ถ้าเป็น list ใช้ IN (...)
            # ใช้ TRIM(sheet) เทียบ เพราะข้อมูลจริงบางค่ามีช่องว่างต่อท้ายปนมา (เช่น
            # "Stamp-3บาท      ") ถ้าเทียบตรงๆ จะไม่เจอแถวไหนเลยแบบเงียบๆ ไม่ error ด้วย
            sheets = sheet if isinstance(sheet, (list, tuple)) else [sheet]
            placeholders = ", ".join("?" for _ in sheets)
            query += f" AND TRIM(sheet) IN ({placeholders})"
            params.extend(s.strip() for s in sheets)
        if bucketid:
            query += " AND bucketid = ?"
            params.append(bucketid)
        if trigger_type:
            query += " AND trigger_type = ?"
            params.append(trigger_type)
        if start_row or end_row:
            start_row = int(start_row) if start_row else 1
            if end_row:
                query += " LIMIT ? OFFSET ?"
                params.extend([int(end_row) - start_row + 1, start_row - 1])
            else:
                query += " LIMIT -1 OFFSET ?"
                params.append(start_row - 1)
        cur.execute(query, params)
        rows = []
        for record in cur.fetchall():
            row = dict(record)
            row["barcode"] = str(row["barcode"]).replace("*", "").strip()
            row["trigger_value"] = int(str(row["trigger_value"]).replace("*", "").strip())
            # reward_type บางแบบ (เช่น Free Item) ไม่มี reward_value เลย (ว่างเปล่า)
            # เก็บเป็น None แทนที่จะพังตอนแปลงเป็น float
            reward_value = str(row["reward_value"]).replace("*", "").strip()
            row["reward_value"] = float(reward_value) if reward_value else None
            rows.append(row)
        conn.close()
        return rows

    @keyword
    def group_rows_by_promotion(self, rows):
        # จัดกลุ่มแถวตาม promotion_code โดย "รักษาลำดับที่พบครั้งแรกในผลลัพธ์ query เดิมไว้"
        # (แต่ละ promotion_code ทั้งกลุ่มมี trigger_type เดียวกันเสมอ — ตรวจสอบกับข้อมูลจริงแล้ว
        # ไม่มี promotion_code ไหนปนกันระหว่าง ItemSpend/Quantity) เพื่อให้ Robot วนประมวลผล
        # ทีละ promotion_code ตามลำดับที่อยู่ในฐานข้อมูลจริง แล้วค่อยเช็ค trigger_type ของแต่ละ
        # กลุ่มด้วย IF ว่าจะเข้า flow ไหน (Quantity หรือ ItemSpend) แทนที่จะแยกกองทำ ItemSpend
        # ทั้งหมดก่อนแล้วค่อยทำ Quantity ทั้งหมดทีหลัง
        #
        # คืนค่าเป็น list ของ dict แต่ละอันมี promotion_code, promotion_name, trigger_type,
        # trigger_value, member_segmentation (จากแถวแรกของกลุ่ม), barcodes (list บาร์โค้ดทุกตัว
        # ในกลุ่มเรียงตามลำดับเดิม — ใช้กับ flow ItemSpend) และ buckets (list ของ list dict
        # {barcode, entity_code, entity_name} แยกตาม bucketid เรียงตามลำดับที่เจอก่อน-หลัง —
        # ใช้กับ flow Quantity เก็บ entity_code/entity_name ไว้ด้วยเพื่อ log ว่าแต่ละบิลขายสินค้าอะไร)
        groups = {}
        order = []
        for row in rows:
            code = row["promotion_code"]
            if code not in groups:
                groups[code] = {
                    "promotion_code": code,
                    "promotion_name": row["promotion_name"],
                    "trigger_type": row["trigger_type"],
                    "trigger_value": row["trigger_value"],
                    "member_segmentation": row["member_segmentation"],
                    "barcodes": [],
                    "bucket_order": [],
                    "bucket_map": {},
                }
                order.append(code)
            group = groups[code]
            group["barcodes"].append(row["barcode"])
            bucket = row["bucketid"]
            if bucket not in group["bucket_map"]:
                group["bucket_map"][bucket] = []
                group["bucket_order"].append(bucket)
            group["bucket_map"][bucket].append({
                "barcode": row["barcode"],
                "entity_code": row["entity_code"],
                "entity_name": row["entity_name"],
            })

        result = []
        for code in order:
            group = groups[code]
            buckets = [group["bucket_map"][b] for b in group["bucket_order"]]
            result.append({
                "promotion_code": group["promotion_code"],
                "promotion_name": group["promotion_name"],
                "trigger_type": group["trigger_type"],
                "trigger_value": group["trigger_value"],
                "member_segmentation": group["member_segmentation"],
                "barcodes": group["barcodes"],
                "buckets": buckets,
            })
        return result

    @keyword
    def get_sale_price_from_barcode(self, db_path, barcode):
        # หาราคาต่อชิ้นจากตาราง products (คนละตารางกับ promotion_data) ด้วยบาร์โค้ด
        # ใช้สำหรับ trigger_type=ItemSpend คำนวณล่วงหน้าว่าต้องซื้อกี่ชิ้นถึงจะครบยอดขั้นต่ำ
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute("SELECT SALE_PRICE FROM products WHERE BARCODE = ?", (barcode,))
        record = cur.fetchone()
        conn.close()
        if not record:
            raise ValueError(f"ไม่พบราคาสินค้าในตาราง products สำหรับบาร์โค้ด {barcode!r}")
        return float(str(record[0]).replace("*", "").strip())
