#!/usr/bin/env python3
# import_meals_fast.py

import pandas as pd
import sqlite3
from datetime import date
import sys

def import_meals(excel_file, db_file, year, month, meal_type):
    # Đọc dữ liệu Excel
    df = pd.read_excel(excel_file, engine="openpyxl")
    # Cột họ và tên đệm (cột B) và tên (cột C)
    col_surname = df.columns[1]
    col_name    = df.columns[2]
    # Các cột ngày: tên cột là số nguyên (1,2,...,31)
    date_cols = [c for c in df.columns if isinstance(c, int)]
    
    conn = sqlite3.connect(db_file)
    cur  = conn.cursor()
    imported = 0

    for _, row in df.iterrows():
        surname   = str(row[col_surname]).strip()
        firstname = str(row[col_name]).strip()
        fullname  = f"{surname} {firstname}"
        # Lấy student_id từ cột name trong DB
        cur.execute("SELECT id FROM meals_student WHERE name = ?", (fullname,))
        res = cur.fetchone()
        if not res:
            print(f"⚠️ Không tìm thấy học sinh '{fullname}'")
            continue
        student_id = res[0]
        
        for day in date_cols:
            val = row[day]
            if pd.isna(val):
                continue
            try:
                meal_date = date(int(year), int(month), int(day))
            except ValueError:
                print(f"⚠️ Ngày không hợp lệ: {day}")
                continue
            # Mapping ký tự P/KP/x sang status & non_eat
            if val == 'P':
                status, non_eat = 'thiếu', 1
            elif val == 'KP':
                status, non_eat = 'thiếu', 2
            elif val == 'x':
                status, non_eat = 'đủ', 0
            else:
                continue
            cur.execute(
                "INSERT INTO meals_mealrecord (student_id, date, meal_type, status, non_eat) VALUES (?, ?, ?, ?, ?)",
                (student_id, meal_date, meal_type, status, non_eat)
            )
            imported += 1

    conn.commit()
    conn.close()
    print(f"✅ Đã import thành công {imported} bản ghi cho bữa '{meal_type}'.")

if __name__ == "__main__":
    if len(sys.argv) != 6:
        print("Usage: python import_meals_fast.py <excel_file> <db_file> <year> <month> <meal_type>")
        sys.exit(1)
    _, excel_file, db_file, year, month, meal_type = sys.argv
    import_meals(excel_file, db_file, year, month, meal_type)
