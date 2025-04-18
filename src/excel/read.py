import pandas as pd

try:
    # Read all sheets from the Excel file
    print("Reading Excel file...")
    df_dict = pd.read_excel('DF format.xlsx', sheet_name=None)
    
    # Print available sheets
    print(f"Available sheets: {list(df_dict.keys())}")
    
    # Print information about each sheet
    for sheet_name, df in df_dict.items():
        print(f"\nSheet: {sheet_name}")
        print(f"Shape: {df.shape}")
        print(f"Columns: {df.columns.tolist()}")
        print("Sample data:")
        print(df.head(3))
except Exception as e:
    print(f"Error reading Excel file: {e}") 