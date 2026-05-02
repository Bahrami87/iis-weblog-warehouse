import sqlite3
import pathlib
import pandas as pd
from datetime import datetime
from .config import STAGE3_CSV, DB_PATH, logger


def _apply_schema(con):
    con.executescript("""
        CREATE TABLE IF NOT EXISTS Dim_Time (
            Time_Key        INTEGER PRIMARY KEY AUTOINCREMENT,
            Full_Date_Time  DATETIME NOT NULL UNIQUE,
            Date            DATE, Time_of_Day TIME,
            Year            INTEGER, Quarter INTEGER,
            Month           INTEGER, Month_Name VARCHAR,
            Day_of_Month    INTEGER, Day_of_Week INTEGER,
            Day_Name        VARCHAR, Week_of_Year INTEGER,
            Is_Weekend      BOOLEAN, Hour_of_Day INTEGER,
            Minute_of_Hour  INTEGER
        );
        CREATE TABLE IF NOT EXISTS Dim_File (
            File_Key        INTEGER PRIMARY KEY AUTOINCREMENT,
            URI_Stem        VARCHAR NOT NULL UNIQUE,
            File_Name       VARCHAR,
            File_Extension  VARCHAR,
            File_Type_Group VARCHAR
        );
        CREATE TABLE IF NOT EXISTS Dim_Client (
            Client_Key       INTEGER PRIMARY KEY AUTOINCREMENT,
            Browser_Name     VARCHAR,
            Browser_Version  VARCHAR,
            Operating_System VARCHAR,
            OS_Version       VARCHAR,
            Is_Crawler       BOOLEAN,
            UNIQUE(Browser_Name, Browser_Version, Operating_System, OS_Version, Is_Crawler)
        );
        CREATE TABLE IF NOT EXISTS Dim_Location (
            Location_Key INTEGER PRIMARY KEY AUTOINCREMENT,
            Client_IP    VARCHAR NOT NULL UNIQUE,
            Country      VARCHAR,
            State_Area   VARCHAR,
            City         VARCHAR,
            Postcode     VARCHAR,
            Latitude     REAL,
            Longitude    REAL
        );
        CREATE TABLE IF NOT EXISTS Dim_RequestStatus (
            RequestStatus_Key INTEGER PRIMARY KEY AUTOINCREMENT,
            Status_Code       INTEGER,
            Substatus_Code    INTEGER,
            Win32_Status_Code INTEGER,
            Is_Error          BOOLEAN,
            UNIQUE(Status_Code, Substatus_Code, Win32_Status_Code)
        );
        CREATE TABLE IF NOT EXISTS Dim_Server (
            Server_Key  INTEGER PRIMARY KEY AUTOINCREMENT,
            Server_IP   VARCHAR,
            Server_Port INTEGER,
            Site_Name   VARCHAR,
            UNIQUE(Server_IP, Server_Port)
        );
        CREATE TABLE IF NOT EXISTS Dim_Referrer (
            Referrer_Key    INTEGER PRIMARY KEY AUTOINCREMENT,
            Referrer_URL    VARCHAR NOT NULL UNIQUE,
            Referrer_Domain VARCHAR
        );
        CREATE TABLE IF NOT EXISTS Fact_WebLog (
            LogEntry_ID       INTEGER PRIMARY KEY AUTOINCREMENT,
            Full_Date_Time_NK DATETIME,
            Time_Key          INTEGER REFERENCES Dim_Time(Time_Key),
            File_Key          INTEGER REFERENCES Dim_File(File_Key),
            Client_Key        INTEGER REFERENCES Dim_Client(Client_Key),
            Location_Key      INTEGER REFERENCES Dim_Location(Location_Key),
            RequestStatus_Key INTEGER REFERENCES Dim_RequestStatus(RequestStatus_Key),
            Server_Key        INTEGER REFERENCES Dim_Server(Server_Key),
            Referrer_Key      INTEGER REFERENCES Dim_Referrer(Referrer_Key),
            Requests_Count    INTEGER DEFAULT 1,
            Bytes_Transferred INTEGER,
            Time_Taken_ms     INTEGER,
            Client_Bytes      INTEGER,
            Is_Error_Flag     BOOLEAN,
            HTTP_Method       VARCHAR,
            URI_Query_NK      VARCHAR,
            Raw_User_Agent_NK VARCHAR,
            Client_IP_Raw_NK  VARCHAR
        );
    """)
    con.commit()


def _file_type(ext):
    ext = (ext or '').lower()
    mapping = {
        '.png': 'Image', '.jpg': 'Image', '.jpeg': 'Image',
        '.gif': 'Image', '.ico': 'Image', '.svg': 'Image',
        '.css': 'Stylesheet',
        '.js':  'Script',
        '.aspx': 'Page', '.asp': 'Page', '.html': 'Page',
        '.htm': 'Page', '.php': 'Page',
        '.pdf': 'Document', '.doc': 'Document', '.docx': 'Document',
    }
    return mapping.get(ext, 'Other')


def _safe(val, default=None):
    """Return None for NaN/None/empty strings, otherwise the value."""
    if val is None:
        return default
    if str(val) in ('nan', 'None', ''):
        return default
    return val


def _load_dim_time(con, df):
    rows, seen = [], set()
    for val in df['Full_Date_Time_NK'].dropna().unique():
        try:
            dt = datetime.strptime(str(val)[:16], '%Y-%m-%d %H:%M')
        except Exception:
            continue
        if dt in seen:
            continue
        seen.add(dt)
        rows.append((
            dt.isoformat(sep=' '),
            dt.date().isoformat(),
            dt.time().isoformat(),
            dt.year,
            (dt.month - 1) // 3 + 1,
            dt.month,
            dt.strftime('%B'),
            dt.day,
            dt.isoweekday(),
            dt.strftime('%A'),
            dt.isocalendar()[1],
            1 if dt.isoweekday() >= 6 else 0,
            dt.hour,
            dt.minute,
        ))
    con.executemany("""
        INSERT OR IGNORE INTO Dim_Time
        (Full_Date_Time, Date, Time_of_Day, Year, Quarter, Month, Month_Name,
         Day_of_Month, Day_of_Week, Day_Name, Week_of_Year, Is_Weekend,
         Hour_of_Day, Minute_of_Hour)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, rows)
    con.commit()
    logger.info(f'  Dim_Time: {len(rows)} new rows')
    cur = con.execute("SELECT Full_Date_Time, Time_Key FROM Dim_Time")
    return {r[0]: r[1] for r in cur.fetchall()}


def _load_dim_file(con, df):
    rows, seen = [], set()
    for stem in df['cs_uri_stem'].dropna().unique():
        stem = str(stem)
        if stem in seen:
            continue
        seen.add(stem)
        p = pathlib.PurePosixPath(stem)
        ext = p.suffix
        rows.append((stem, p.name, ext, _file_type(ext)))
    con.executemany(
        "INSERT OR IGNORE INTO Dim_File (URI_Stem, File_Name, File_Extension, File_Type_Group) VALUES (?,?,?,?)",
        rows
    )
    con.commit()
    logger.info(f'  Dim_File: {len(rows)} new rows')
    cur = con.execute("SELECT URI_Stem, File_Key FROM Dim_File")
    return {r[0]: r[1] for r in cur.fetchall()}


def _load_dim_client(con, df):
    cols = ['browser_name', 'browser_version', 'operating_system', 'os_version', 'is_crawler']
    sub = df[cols].drop_duplicates().fillna('')
    rows = []
    for r in sub.itertuples(index=False):
        is_crawler = 1 if str(r[4]) in ('True', '1', 'true') else 0
        rows.append((str(r[0]), str(r[1]), str(r[2]), str(r[3]), is_crawler))
    con.executemany(
        "INSERT OR IGNORE INTO Dim_Client (Browser_Name, Browser_Version, Operating_System, OS_Version, Is_Crawler) VALUES (?,?,?,?,?)",
        rows
    )
    con.commit()
    logger.info(f'  Dim_Client: {len(rows)} new rows')
    cur = con.execute("SELECT Browser_Name, Browser_Version, Operating_System, OS_Version, Is_Crawler, Client_Key FROM Dim_Client")
    return {(r[0], r[1], r[2], r[3], r[4]): r[5] for r in cur.fetchall()}


def _load_dim_location(con, df):
    cols = ['c_ip', 'country', 'state_area', 'city', 'postcode', 'latitude', 'longitude']
    for c in cols:
        if c not in df.columns:
            df[c] = None
    sub = df[cols].drop_duplicates(subset=['c_ip']).fillna('')
    rows = [tuple(r) for r in sub.itertuples(index=False)]
    con.executemany(
        "INSERT OR IGNORE INTO Dim_Location (Client_IP, Country, State_Area, City, Postcode, Latitude, Longitude) VALUES (?,?,?,?,?,?,?)",
        rows
    )
    con.commit()
    logger.info(f'  Dim_Location: {len(rows)} new rows')
    cur = con.execute("SELECT Client_IP, Location_Key FROM Dim_Location")
    return {r[0]: r[1] for r in cur.fetchall()}


def _load_dim_status(con, df):
    cols = ['sc_status', 'sc_substatus', 'sc_win32_status']
    for c in cols:
        if c not in df.columns:
            df[c] = 0
    sub = df[cols].drop_duplicates().fillna(0)
    rows = []
    for r in sub.itertuples(index=False):
        try:
            code = int(r[0])
        except Exception:
            code = 0
        try:
            sub_s = int(r[1])
        except Exception:
            sub_s = 0
        try:
            win32 = int(r[2])
        except Exception:
            win32 = 0
        rows.append((code, sub_s, win32, 1 if code >= 400 else 0))
    con.executemany(
        "INSERT OR IGNORE INTO Dim_RequestStatus (Status_Code, Substatus_Code, Win32_Status_Code, Is_Error) VALUES (?,?,?,?)",
        rows
    )
    con.commit()
    logger.info(f'  Dim_RequestStatus: {len(rows)} new rows')
    cur = con.execute("SELECT Status_Code, Substatus_Code, Win32_Status_Code, RequestStatus_Key FROM Dim_RequestStatus")
    return {(r[0], r[1], r[2]): r[3] for r in cur.fetchall()}


def _load_dim_server(con, df):
    cols = ['s_ip', 's_port']
    for c in cols:
        if c not in df.columns:
            df[c] = None
    sub = df[cols].drop_duplicates().fillna('')
    rows = []
    for r in sub.itertuples(index=False):
        ip   = str(r[0]).strip()
        port = str(r[1]).strip()
        # Skip rows where server IP was not logged
        if ip in ('', '-', 'nan'):
            continue
        rows.append((ip, port, 'Default Web Site'))
    con.executemany(
        "INSERT OR IGNORE INTO Dim_Server (Server_IP, Server_Port, Site_Name) VALUES (?,?,?)",
        rows
    )
    con.commit()
    logger.info(f'  Dim_Server: {len(rows)} new rows')
    cur = con.execute("SELECT Server_IP, Server_Port, Server_Key FROM Dim_Server")
    return {(r[0], str(r[1])): r[2] for r in cur.fetchall()}


def _load_dim_referrer(con, df):
    if 'cs_referer' not in df.columns:
        return {}
    urls = df['cs_referer'].dropna().unique()
    urls = [u for u in urls if str(u) not in ('', '-')]
    rows = []
    for url in urls:
        try:
            from urllib.parse import urlparse
            domain = urlparse(str(url)).netloc
        except Exception:
            domain = ''
        rows.append((str(url), domain))
    con.executemany(
        "INSERT OR IGNORE INTO Dim_Referrer (Referrer_URL, Referrer_Domain) VALUES (?,?)",
        rows
    )
    con.commit()
    logger.info(f'  Dim_Referrer: {len(rows)} new rows')
    cur = con.execute("SELECT Referrer_URL, Referrer_Key FROM Dim_Referrer")
    return {r[0]: r[1] for r in cur.fetchall()}


def _load_fact(con, df, time_map, file_map, client_map, loc_map, status_map, server_map, ref_map):
    rows = []
    for r in df.itertuples(index=False):

        def g(col, default=None):
            try:
                val = getattr(r, col)
                return default if str(val) in ('nan', 'None', '') else val
            except AttributeError:
                return default

        # Timestamp
        dt_str = str(g('Full_Date_Time_NK', '') or '')
        try:
            dt = datetime.strptime(dt_str[:16], '%Y-%m-%d %H:%M').isoformat(sep=' ')
        except Exception:
            dt = None

        # Status codes — all integers
        try:
            status = int(g('sc_status', 0) or 0)
        except Exception:
            status = 0
        try:
            sub_s = int(g('sc_substatus', 0) or 0)
        except Exception:
            sub_s = 0
        try:
            win32 = int(g('sc_win32_status', 0) or 0)
        except Exception:
            win32 = 0

        is_err = 1 if status >= 400 else 0

        # Client key — is_crawler must be integer to match what _load_dim_client stored
        is_crawler_raw = g('is_crawler', '')
        is_crawler_int = 1 if str(is_crawler_raw) in ('True', '1', 'true') else 0
        client_key_tuple = (
            str(g('browser_name',     '') or ''),
            str(g('browser_version',  '') or ''),
            str(g('operating_system', '') or ''),
            str(g('os_version',       '') or ''),
            is_crawler_int,
        )

        # Server key — both strings to match _load_dim_server
        server_key_tuple = (str(g('s_ip') or ''), str(g('s_port') or ''))

        # Referrer key
        ref_url = g('cs_referer')
        ref_key = ref_map.get(str(ref_url)) if ref_url and str(ref_url) not in ('', '-') else None

        rows.append((
            dt,
            time_map.get(dt),
            file_map.get(g('cs_uri_stem')),
            client_map.get(client_key_tuple),
            loc_map.get(g('c_ip')),
            status_map.get((status, sub_s, win32)),
            server_map.get(server_key_tuple),
            ref_key,
            1,
            _safe(g('sc_bytes')),
            _safe(g('time_taken')),
            _safe(g('cs_bytes')),
            is_err,
            g('cs_method'),
            _safe(g('cs_uri_query')),
            g('cs_user_agent'),
            g('c_ip'),
        ))

    con.executemany("""
        INSERT INTO Fact_WebLog
        (Full_Date_Time_NK, Time_Key, File_Key, Client_Key, Location_Key,
         RequestStatus_Key, Server_Key, Referrer_Key, Requests_Count,
         Bytes_Transferred, Time_Taken_ms, Client_Bytes, Is_Error_Flag,
         HTTP_Method, URI_Query_NK, Raw_User_Agent_NK, Client_IP_Raw_NK)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, rows)
    con.commit()
    logger.info(f'  Inserted {len(rows)} rows into Fact_WebLog')


# Entry point — kept at the bottom so all helpers are defined before it is called

def load_warehouse(df: pd.DataFrame = None):
    if df is None:
        df = pd.read_csv(STAGE3_CSV)
    logger.info(f'[Stage 4/4] Loading warehouse ({DB_PATH.name})')
    if DB_PATH.exists():
        DB_PATH.unlink()
    con = sqlite3.connect(DB_PATH)
    _apply_schema(con)

    # Combine date + time columns into a single timestamp
    if 'date' in df.columns and 'time' in df.columns:
        df['Full_Date_Time_NK'] = df['date'].astype(str) + ' ' + df['time'].astype(str)
    else:
        df['Full_Date_Time_NK'] = None

    time_map   = _load_dim_time(con, df)
    file_map   = _load_dim_file(con, df)
    client_map = _load_dim_client(con, df)
    loc_map    = _load_dim_location(con, df)
    status_map = _load_dim_status(con, df)
    server_map = _load_dim_server(con, df)
    ref_map    = _load_dim_referrer(con, df)
    _load_fact(con, df, time_map, file_map, client_map, loc_map, status_map, server_map, ref_map)
    con.close()