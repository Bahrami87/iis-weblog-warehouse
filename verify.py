import sqlite3

con = sqlite3.connect('iis_web_log_warehouse.db')

print('=== WAREHOUSE SUMMARY ===')
for table in ['Fact_WebLog','Dim_Time','Dim_File','Dim_Client','Dim_Location','Dim_RequestStatus','Dim_Server','Dim_Referrer']:
    count = con.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0]
    print(f'  {table:<25} {count:>8,} rows')

print('\n=== TOP 10 COUNTRIES BY TRAFFIC ===')
for r in con.execute('''
    SELECT l.Country, COUNT(*) AS Requests,
           ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM Fact_WebLog), 1) AS Pct
    FROM Fact_WebLog fw JOIN Dim_Location l USING (Location_Key)
    WHERE l.Country IS NOT NULL AND l.Country != ""
    GROUP BY l.Country ORDER BY Requests DESC LIMIT 10
''').fetchall():
    print(f'  {r[0]:<30} {r[1]:>8,}  ({r[2]}%)')

print('\n=== ERROR RATE BY FILE TYPE ===')
for r in con.execute('''
    SELECT f.File_Type_Group, COUNT(*) AS Requests,
           SUM(fw.Is_Error_Flag) AS Errors,
           ROUND(100.0 * SUM(fw.Is_Error_Flag) / COUNT(*), 1) AS Pct_Errors
    FROM Fact_WebLog fw JOIN Dim_File f USING (File_Key)
    GROUP BY f.File_Type_Group ORDER BY Requests DESC
''').fetchall():
    print(f'  {r[0]:<15} {r[1]:>8,} requests   {r[3]:>5}% errors')

print('\n=== TOP 5 BROWSERS (humans only) ===')
for r in con.execute('''
    SELECT c.Browser_Name, COUNT(*) AS Requests
    FROM Fact_WebLog fw JOIN Dim_Client c USING (Client_Key)
    WHERE c.Is_Crawler = 0
    GROUP BY c.Browser_Name ORDER BY Requests DESC LIMIT 5
''').fetchall():
    print(f'  {r[0]:<25} {r[1]:>8,}')

print('\n=== TOP 5 BOTS ===')
for r in con.execute('''
    SELECT c.Browser_Name, COUNT(*) AS Requests
    FROM Fact_WebLog fw JOIN Dim_Client c USING (Client_Key)
    WHERE c.Is_Crawler = 1
    GROUP BY c.Browser_Name ORDER BY Requests DESC LIMIT 5
''').fetchall():
    print(f'  {r[0]:<25} {r[1]:>8,}')

print('\n=== BOTS vs HUMANS ===')
for r in con.execute('''
    SELECT c.Is_Crawler,
           COUNT(*) AS Requests,
           ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM Fact_WebLog), 1) AS Pct
    FROM Fact_WebLog fw JOIN Dim_Client c USING (Client_Key)
    GROUP BY c.Is_Crawler
''').fetchall():
    label = 'Bots  ' if r[0] else 'Humans'
    print(f'  {label}  {r[1]:>8,}  ({r[2]}%)')

print('\n=== ERROR RATE SUMMARY ===')
total, errors = con.execute('''
    SELECT COUNT(*), SUM(Is_Error_Flag) FROM Fact_WebLog
''').fetchone()
print(f'  Total requests : {total:>8,}')
print(f'  Errors (4xx/5xx): {errors:>7,}')
print(f'  Error rate     : {100*errors/total:>7.1f}%')

print('\n=== TRAFFIC BY YEAR-MONTH ===')
for r in con.execute('''
    SELECT t.Year, t.Month_Name, COUNT(*) AS Requests
    FROM Fact_WebLog fw JOIN Dim_Time t USING (Time_Key)
    GROUP BY t.Year, t.Month ORDER BY t.Year, t.Month
''').fetchall():
    print(f'  {r[0]} {r[1]:<12} {r[2]:>8,}')