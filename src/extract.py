import pathlib
import pandas as pd
from .config import LOG_DIRECTORY, CONSOLIDATED_CSV, logger

# Canonical output columns — superset of all field variants in these logs
OUT_COLS = [
    'date', 'time', 's_ip', 'cs_method', 'cs_uri_stem', 'cs_uri_query',
    's_port', 'cs_username', 'c_ip', 'cs_user_agent', 'cs_cookie',
    'cs_referer', 'sc_status', 'sc_substatus', 'sc_win32_status',
    'sc_bytes', 'cs_bytes', 'time_taken'
]


def _normalise(name):
    return (name.replace('-', '_')
                .replace('(', '_')
                .replace(')', '')
                .replace('__', '_')
                .lower())


def extract_logs(log_dir: pathlib.Path = LOG_DIRECTORY) -> pd.DataFrame:
    log_files = list(log_dir.glob('*.log'))
    logger.info('[Stage 1/4] Extracting + consolidating IIS log files')

    frames = []
    for f in sorted(log_files):
        current_fields = None
        current_rows = []
        sections = []

        for line in open(f, encoding='utf-8', errors='replace'):
            line = line.rstrip('\r\n')

            if line.startswith('#Fields:'):
                if current_fields and current_rows:
                    sections.append((current_fields[:], current_rows[:]))
                raw = line[len('#Fields:'):].strip().split()
                current_fields = [_normalise(r) for r in raw]
                current_rows = []

            elif line.startswith('#') or not line.strip():
                continue

            elif current_fields:
                parts = line.split(' ')
                n = len(current_fields)
                if len(parts) >= n:
                    current_rows.append(parts[:n])
                else:
                    current_rows.append(parts + ['-'] * (n - len(parts)))

        if current_fields and current_rows:
            sections.append((current_fields, current_rows))

        for fields, rows in sections:
            df = pd.DataFrame(rows, columns=fields)
            for col in OUT_COLS:
                if col not in df.columns:
                    df[col] = '-'
            frames.append(df[OUT_COLS])

    if frames:
        result = pd.concat(frames, ignore_index=True)
    else:
        result = pd.DataFrame(columns=OUT_COLS)

    # Keep only rows with valid HTTP status codes
    result = result[result['sc_status'].str.match(r'^[2345]\d\d$', na=False)].copy()
    result.reset_index(drop=True, inplace=True)

    result.to_csv(CONSOLIDATED_CSV, index=False)
    logger.info(f'  Consolidated {len(log_files)} log files -> {len(result)} rows -> {CONSOLIDATED_CSV.name}')
    return result