import pandas as pd
import sys
import os

# Check if a file path is provided as a command-line argument
if len(sys.argv) > 1:
    input_file = sys.argv[1]
else:
    # If no argument is provided, prompt the user for the file path
    input_file = input("Enter the path to your Excel file (e.g., 'filename.xlsx'): ").strip()

# Extract the base name of the input file (without extension)
base_name = os.path.splitext(os.path.basename(input_file))[0]

# Read all sheets from the Excel file
excel_file = pd.ExcelFile(input_file)

# Loop through each sheet and save it as a separate Excel file
for sheet_name in excel_file.sheet_names:
    # Read the sheet into a DataFrame
    df = pd.read_excel(input_file, sheet_name=sheet_name)
    
    # Define the output file name in the format "original_filename_sheetname.xlsx"
    output_file = f"{base_name}_{sheet_name}.xlsx"
    
    # Save the DataFrame to a new Excel file
    df.to_excel(output_file, sheet_name=sheet_name, index=False)
    print(f"Saved sheet '{sheet_name}' to '{output_file}'")