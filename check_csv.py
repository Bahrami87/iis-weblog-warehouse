import pandas as pd

df = pd.read_csv('consolidated_iis_logs.csv', dtype=str, low_memory=False)
print('Columns:', list(df.columns))
print()
print('sc_status values:', df['sc_status'].value_counts().head(5).to_dict())
print()
print('First 3 rows full:')
print(df.head(3).to_string())