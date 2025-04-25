#!/usr/bin/env python3
import pandas as pd
import sqlite3
from datetime import date
import sys, os, re, glob
from collections import defaultdict
import calendar

# Hàm import một file và trả về tập tên trùng lặp (duplicate)
def import_meals(excel_file, db_file, year, month):
    # Đọc Excel, header ở dòng 3
    df = pd.read_excel(excel_file, header=2, engine="openpyxl")
    col_surname = df.columns[1]
    col_name    = df.columns[2]
    df = df[df[col_surname].notna() & df[col_name].notna()]

    # Xác định số ngày trong tháng và cột tương ứng
    max_day = calendar.monthrange(int(year), int(month))[1]
    all_date_cols = df.columns[3:]
    date_cols = [c for c in all_date_cols if re.fullmatch(r"\d+", str(c)) and 1 <= int(c) <= max_day]
    if len(date_cols) < max_day:
        print(f"⚠️ Template Excel chỉ có {len(date_cols)} cột ngày, thiếu ngày {len(date_cols)+1}→{max_day}")

    conn = sqlite3.connect(db_file)
    cur  = conn.cursor()
    imported = 0
    counts = defaultdict(int)
    duplicates = set()

    # Log file riêng cho mỗi excel
    basename = os.path.splitext(os.path.basename(excel_file))[0]
    log_filename = f"{basename}_duplicates.txt"
    # Mở file log ở chế độ ghi mới
    log_f = open(log_filename, 'w', encoding='utf-8')

    for _, row in df.iterrows():
        surname   = str(row[col_surname]).strip()
        firstname = str(row[col_name]).strip()
        fullname  = f"{surname} {firstname}"
        if not surname or not firstname:
            continue

        counts[fullname] += 1
        occ = counts[fullname]
        if occ == 1:
            meal_type = "Bữa sáng"
        elif occ == 2:
            meal_type = "Bữa trưa"
        else:
            continue

        # Lấy student_id
        cur.execute("SELECT id FROM meals_student WHERE name = ?", (fullname,))
        res = cur.fetchone()
        if not res:
            print(f"⚠️ Không tìm thấy học sinh '{fullname}'")
            continue
        student_id = res[0]

        # Duyệt theo từng ngày trong tháng
        for col in date_cols:
            val = row[col]
            if pd.isna(val):
                continue
            try:
                day = int(col)
                meal_date = date(int(year), int(month), day)
            except:
                continue

            if val == "P":
                status, non_eat = "Thiếu", 1
            elif val in ("KP", "0"):
                status, non_eat = "Thiếu", 2
            elif str(val).lower() == "x":
                status, non_eat = "Đủ", 0
            else:
                continue

            try:
                cur.execute(
                    "INSERT INTO meals_mealrecord (student_id, date, meal_type, status, non_eat) VALUES (?, ?, ?, ?, ?)",
                    (student_id, meal_date, meal_type, status, non_eat)
                )
                imported += 1
            except sqlite3.IntegrityError:
                # Gặp trùng: in và ghi log vào file riêng
                print(f"⚠️ Đã tồn tại: {fullname}")
                log_f.write(f"{fullname}\n")
                duplicates.add(fullname)
                continue

    conn.commit()
    conn.close()
    log_f.close()

    print(f"✅ {os.path.basename(excel_file)}: imported {imported} records.")
    if duplicates:
        print(f"→ Đã log {len(duplicates)} tên trùng vào {log_filename}")
    return duplicates


def usage():
    print("Usage:")
    print("  # single-file mode:")
    print("  python fast_import.py <excel_file> <db_file> <year> <month>")
    print("  # batch mode (folder or glob):")
    print("  python fast_import.py <folder_or_pattern> <db_file>")
    sys.exit(1)


if __name__ == "__main__":
    args = sys.argv[1:]
    today_year = date.today().year

    # Batch mode
    if len(args) == 2:
        src, db_file = args

        # Lấy danh sách file
        if os.path.isdir(src):
            files = [os.path.join(src, f) for f in os.listdir(src) if f.lower().endswith('.xlsx')]
        else:
            files = glob.glob(src)
        if not files:
            print("⚠️ Không tìm thấy file nào phù hợp.")
            sys.exit(1)

        for f in sorted(files):
            name = os.path.basename(f)
            m = re.search(r"(\d+)", name)
            if not m:
                print(f"⚠️ Không tìm thấy số trong tên file '{name}', bỏ qua.")
                continue
            x = int(m.group(1))
            if x > 7:
                year = today_year - 1
                month = x
            else:
                year = today_year
                month = x

            print(f"→ Processing {name}: year={year}, month={month}")
            duplicates = import_meals(f, db_file, year, month)

    # Single-file mode
    elif len(args) == 4:
        excel_file, db_file, year, month = args
        duplicates = import_meals(excel_file, db_file, year, month)

    else:
        usage()