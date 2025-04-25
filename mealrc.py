#!/usr/bin/env python3
import sys, os, re, glob
import pandas as pd
import sqlite3
from datetime import date
from collections import defaultdict

# Map chỉ số cột Excel -> tên
COL_MAP = {34: 'AI', 35: 'AJ', 36: 'AK', 37: 'AL'}

MISSING_LOG = 'missing_names_payment.txt'

def extract_data(path):
    """
    Trả về list dict kết quả tính toán từ file Excel
    và set tên học sinh không tìm thấy trong DB.
    """
    df = pd.read_excel(path, header=None, engine='openpyxl')
    # build dict {fullname: {'first_AJ':..., 'second': {...}}}
    stu = {}
    for _, row in df.iterrows():
        # lấy 4 cột số
        vals = {}
        for idx, name in COL_MAP.items():
            raw = row.iloc[idx]
            num = pd.to_numeric(raw, errors='coerce')
            vals[name] = float(num) if pd.notna(num) else None

        # ghép họ + tên
        p1 = str(row.iloc[1]).strip() if not pd.isna(row.iloc[1]) else ''
        p2 = str(row.iloc[2]).strip() if not pd.isna(row.iloc[2]) else ''
        fullname = " ".join((p1 + " " + p2).split())
        if not fullname or fullname.lower().startswith("họ và tên"):
            continue

        if fullname not in stu:
            stu[fullname] = {'first_AJ': None, 'second': None}
        non_null = {k: v for k, v in vals.items() if v is not None}
        # lần đầu chỉ 2 giá trị (chắc AJ), lần sau đủ 4
        if len(non_null) == 2 and 'AJ' in non_null:
            stu[fullname]['first_AJ'] = vals['AJ']
        elif len(non_null) == 4:
            stu[fullname]['second'] = vals

    results = []
    missing = set()
    for name, data in stu.items():
        AJ1 = data['first_AJ']
        sec = data['second']
        if AJ1 is None or sec is None:
            # thiếu dữ liệu → skip luôn
            print(f"Missing data for {name}, bỏ qua.")
            continue

        AI = sec['AI']
        AJ2 = sec['AJ']
        AK  = sec['AK']
        AL  = sec['AL']
        tien_an = AL - AJ1
        if not AI or AI == 0:
            print(f"Warning: AI=0 cho {name}, bỏ qua.")
            continue

        rate = tien_an / AI
        if rate == 30:
            mp_id = 2
        elif rate == 20:
            mp_id = 1
        else:
            print(f"Warning: rate={rate} không khớp 20/30 cho {name}, bỏ qua.")
            continue

        results.append({
            'name': name,
            'tuition_fee': AK * 1000,
            'amount_paid': AJ2 * 1000,
            'remaining_balance': 0,
            'meal_price_id': mp_id
        })
    return results

def process_file(xlsx, dbf, month_str):
    """
    Import/update dữ liệu của 1 file vào meals_studentpayment, 
    ghi lại missing student vào MISSING_LOG.
    """
    print(f"\n→ Processing {os.path.basename(xlsx)} for month {month_str}")
    data = extract_data(xlsx)
    conn = sqlite3.connect(dbf)
    cur  = conn.cursor()
    missing_db = []
    for r in data:
        # lookup student_id
        cur.execute("SELECT id FROM meals_student WHERE name = ?", (r['name'],))
        row = cur.fetchone()
        if not row:
            print(f"Chưa tìm thấy học sinh '{r['name']}', bỏ qua.")
            missing_db.append(r['name'])
            continue
        sid = row[0]
        # check đã có payment?
        cur.execute("SELECT id FROM meals_studentpayment WHERE student_id = ? AND month = ?",
                    (sid, month_str))
        ex = cur.fetchone()
        if ex:
            cur.execute("""
                UPDATE meals_studentpayment
                SET tuition_fee=?, amount_paid=?, remaining_balance=?, meal_price_id=?
                WHERE student_id=? AND month=?
            """, (r['tuition_fee'], r['amount_paid'], r['remaining_balance'],
                  r['meal_price_id'], sid, month_str))
            print(f"Updated {r['name']}")
        else:
            cur.execute("""
                INSERT INTO meals_studentpayment
                  (month, tuition_fee, amount_paid, remaining_balance, student_id, meal_price_id)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (month_str, r['tuition_fee'], r['amount_paid'], r['remaining_balance'],
                  sid, r['meal_price_id']))
            print(f"Inserted {r['name']}")
    conn.commit()
    conn.close()

    # ghi missing xuống file
    if missing_db:
        with open(MISSING_LOG, 'a', encoding='utf-8') as flog:
            for name in missing_db:
                flog.write(f"{name}_{os.path.basename(xlsx)}\n")
        print(f"→ Logged {len(missing_db)} missing names to {MISSING_LOG}")

def usage():
    print("Usage:")
    print("  # single-file:")
    print("  python mealrc.py input.xlsx site.db YYYY-MM")
    print("  python mealrc.py input.xlsx site.db YYYY MM")
    print("  # batch (folder or glob):")
    print("  python mealrc.py <folder_or_pattern> site.db")
    sys.exit(1)

if __name__ == "__main__":
    args = sys.argv[1:]
    today = date.today()
    # --- batch mode: 2 args ---
    if len(args) == 2:
        src, dbf = args
        # reset log
        open(MISSING_LOG, 'w', encoding='utf-8').close()
        # list files
        if os.path.isdir(src):
            files = [os.path.join(src, f) for f in os.listdir(src) if f.lower().endswith('.xlsx')]
        else:
            files = glob.glob(src)
        if not files:
            print("⚠️ Không tìm thấy file nào phù hợp.")
            sys.exit(1)
        for f in sorted(files):
            name = os.path.basename(f)
            m = re.search(r'(\d+)', name)
            if not m:
                print(f"⚠️ Không tìm thấy số trong tên file '{name}', bỏ qua.")
                continue
            x = int(m.group(1))
            if x > 7:
                yr = today.year - 1
                mo = x
            else:
                yr = today.year
                mo = x
            month_str = f"{yr}-{mo:02d}"
            process_file(f, dbf, month_str)

    # --- single-file: YYYY-MM ---
    elif len(args) == 3:
        xlsx, dbf, month_str = args
        # validate format
        if not re.match(r'^\d{4}-\d{2}$', month_str):
            print("⚠️ Tháng phải ở dạng YYYY-MM")
            usage()
        process_file(xlsx, dbf, month_str)

    # --- single-file: YYYY MM ---
    elif len(args) == 4:
        xlsx, dbf, yr, mo = args
        try:
            ym = f"{int(yr):04d}-{int(mo):02d}"
        except:
            print("⚠️ Năm/tháng không hợp lệ.")
            usage()
        process_file(xlsx, dbf, ym)

    else:
        usage()
