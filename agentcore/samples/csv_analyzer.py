import pandas as pd

def analyze_csv(file_path):
    df = pd.read_csv(file_path)
    
    print(f"CSV Analysis for: {file_path}")
    print("=" * (18 + len(file_path)))
    print()
    print(f"Size: {len(df)} x {len(df.columns)} (rows x columns)")
    print(f"\nColumn Headers: {', '.join(list(df.columns))}")
    print(f"\nData Types:")
    for col, dtype in df.dtypes.items():
        print(f"  {col}: {dtype}")
    print()
    print(df.describe(include='all'))

if __name__ == "__main__":
    analyze_csv("sample_data.csv")
