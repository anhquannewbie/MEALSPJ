#!/usr/bin/env python3
# fast_import.py

import pandas as pd
import sqlite3
from datetime import date
import sys
from collections import defaultdict

def import_meals(excel_file, db_file, year, month):
    # Đọc dữ liệu Excel, header tại dòng 3 (index=2)
    df = pd.read_excel(excel_file, header=2, engine="openpyxl")
    # Xác định cột họ và tên đệm (B, index=1) và tên (C, index=2)
    col_surname = df.columns[1]
    col_name    = df.columns[2]
    # Lọc chỉ các dòng có tên học sinh (loại bỏ những hàng header phụ, note)
    df = df[df[col_surname].notna() & df[col_name].notna()]
    # Các cột ngày: từ D (index 3) đến AH (index 33)
    date_cols = df.columns[3:34]
    
    conn = sqlite3.connect(db_file)
    cur  = conn.cursor()
    imported = 0
    counts = defaultdict(int)

    for _, row in df.iterrows():
        surname   = str(row[col_surname]).strip()
        firstname = str(row[col_name]).strip()
        fullname  = f"{surname} {firstname}"
        if not surname or not firstname:
            continue
        counts[fullname] += 1
        occ = counts[fullname]
        # Xác định bữa: lần 1 = sáng, lần 2 = trưa
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

        # Insert bản ghi theo ngày
        for col in date_cols:
            val = row[col]
            if pd.isna(val):
                continue
            # col là tiêu đề cột string hoặc int
            try:
                day = int(col)
            except:
                continue
            # Xây ngày
            try:
                meal_date = date(int(year), int(month), day)
            except ValueError:
                print(f"⚠️ Ngày không hợp lệ: {day}")
                continue
            # Mapping ký tự P/KP/x
            if val == "P":
                status, non_eat = "Thiếu", 1
            elif val == "KP" or val=="0":
                status, non_eat = "Thiếu", 2
            elif val == "x":
                status, non_eat = "Đủ", 0
            else:
                continue

            cur.execute(
                "INSERT INTO meals_mealrecord (student_id, date, meal_type, status, non_eat) VALUES (?, ?, ?, ?, ?)",
                (student_id, meal_date, meal_type, status, non_eat)
            )
            imported += 1

    conn.commit()
    conn.close()
    print(f"✅ Đã import thành công {imported} bản ghi (bao gồm cả sáng & trưa).")

if __name__ == "__main__":
    if len(sys.argv) != 5:
        print("Usage: python fast_import.py <excel_file> <db_file> <year> <month>")
        sys.exit(1)
    _, excel_file, db_file, year, month = sys.argv
    import_meals(excel_file, db_file, year, month)
