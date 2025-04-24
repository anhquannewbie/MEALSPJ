import pandas as pd
import glob

# bước 1: tìm 4 file vừa sinh
files = glob.glob('s*.xlsx') + glob.glob('t*.xlsx')

for f in files:
    # đọc vào, bỏ 2 dòng đầu
    df = pd.read_excel(f, skiprows=2, engine='openpyxl')
    # xoá cột D (index 3)
    df.drop(df.columns[3], axis=1, inplace=True)

    # bước 2: xác định các cột ngày (tên cột chỉ toàn chữ số)
    day_cols = [c for c in df.columns if str(c).strip().isdigit()]

    # bước 3: thay tất cả giá trị = 0 thành "KP"
    for c in day_cols:
        df[c] = df[c].apply(lambda x: 'KP' if x == 0 else x)

    # lưu đè lại file
    df.to_excel(f, index=False)
    print(f"Processed: {f}")
