
import pandas as pd
import os
import sys

def save_worksheets_to_files(file_path):
    # Kiểm tra xem file có tồn tại không
    if not os.path.exists(file_path):
        print(f"File {file_path} không tồn tại!")
        return
    
    # Đọc file Excel
    try:
        excel_file = pd.ExcelFile(file_path)
    except Exception as e:
        print(f"Lỗi khi đọc file Excel: {e}")
        return
    
    # Lấy tên file gốc mà không có phần mở rộng
    file_name = os.path.splitext(os.path.basename(file_path))[0]
    
    # Bỏ 2 ký tự đầu và 5 ký tự cuối
    if len(file_name) > 7:
        modified_file_name = file_name[2:-5]
    else:
        modified_file_name = file_name  # Nếu tên file quá ngắn, giữ nguyên
    
    # Lặp qua từng worksheet
    for sheet_name in excel_file.sheet_names:
        # Đọc dữ liệu từ worksheet
        df = pd.read_excel(file_path, sheet_name=sheet_name)
        
        # Thay thế giá trị 0 thành "KP" trong các cột từ cột 3 đến cột 33 (index 2 đến 32)
        for col in df.columns[2:33]:  # Cột 3 đến 33 (index 2 đến 32)
            if col in df.columns:  # Kiểm tra cột có tồn tại
                df[col] = df[col].replace(0, "KP")
        
        # Tạo tên file mới
        new_file_name = f"{sheet_name}_{modified_file_name}.xlsx"
        
        # Lưu vào file Excel mới
        df.to_excel(new_file_name, index=False)
        print(f"Đã lưu: {new_file_name}")

# Kiểm tra tham số dòng lệnh
if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Cách sử dụng: python split_excel_worksheets.py <đường_dẫn_file_excel>")
        sys.exit(1)
    
    file_path = sys.argv[1]
    save_worksheets_to_files(file_path)
