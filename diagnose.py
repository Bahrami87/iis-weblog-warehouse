import sqlite3
import pandas as pd

# Check 1: Is_Error_Flag in the database
con = sqlite3.connect('iis_web_log_warehouse.db')
print('=== Is_Error_Flag distribution ===')
for r in con.execute('SELECT Is_Error_Flag, COUNT(*) FROM Fact_WebLog GROUP BY Is_Error_Flag').fetchall():
    print(f'  Is_Error_Flag={r[0]}  count={r[1]:,}')

print('\n=== Sample 404/500 rows in fact table ===')
for r in con.execute('''
    SELECT fw.Is_Error_Flag, rs.Status_Code, fw.Client_IP_Raw_NK
    FROM Fact_WebLog fw JOIN Dim_RequestStatus rs USING (RequestStatus_Key)
    WHERE rs.Status_Code IN (404, 500)
    LIMIT 5
''').fetchall():
    print(r)

# Check 2: sc_status raw values in stage3.csv
print('\n=== sc_status sample from stage3.csv ===')
df = pd.read_csv('stage3.csv', dtype=str, low_memory=False)
print('dtype:', df['sc_status'].dtype)
print('sample values:', df['sc_status'].value_counts().head(8).to_dict())

# Check 3: IE crawler flag in stage3.csv
print('\n=== IE crawler flag sample ===')
ie = df[df['browser_name'] == 'IE'][['c_ip','browser_name','is_crawler']].head(5)
print(ie.to_string())

# Check 4: What IPs are flagged as crawlers with IE browser
print('\n=== Crawler IPs using IE (first 5) ===')
crawler_ie = df[(df['browser_name'] == 'IE') & (df['is_crawler'] == 'True')]
print(f'Total IE rows flagged as crawler: {len(crawler_ie):,}')
if len(crawler_ie) > 0:
    print(crawler_ie[['c_ip','cs_uri_stem','cs_user_agent']].head(3).to_string())