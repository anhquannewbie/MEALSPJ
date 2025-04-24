import sqlite3
import os

# Đường dẫn đến DB và SQL
BASE = r"C:\Users\DANG ANH QUAN\Documents\GitHub\MEALSPJ"
DB   = os.path.join(BASE, "site.db")
SQL  = os.path.join(BASE, "import_meals.sql")

# Đọc các câu lệnh SQL từ file, bỏ dòng trống
with open(SQL, encoding='utf-8') as f:
    lines = [line.strip() for line in f if line.strip()]

# Kết nối SQLite
conn = sqlite3.connect(DB)
cur  = conn.cursor()

# Thực thi từng lệnh và bỏ qua lỗi NOT NULL / thiếu student_id
imported = 0
for line in lines:
    try:
        cur.execute(line)
        imported += 1
    except sqlite3.IntegrityError:
        # Bỏ qua các lỗi ràng buộc, ví dụ student_id NULL
        continue

conn.commit()
conn.close()

print(f"✅ Đã import thành công {imported} bản ghi, bỏ qua các dòng thiếu student_id.")
