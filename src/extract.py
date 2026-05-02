import pathlib
import pandas as pd
from .config import LOG_DIRECTORY, CONSOLIDATED_CSV, logger

IIS_FIELDS = [
    'date', 'time', 's_ip', 'cs_method', 'cs_uri_stem', 'cs_uri_query',
    's_port', 'cs_username', 'c_ip', 'cs_user_agent', 'cs_referer',
    'sc_status', 'sc_substatus', 'sc_win32_status', 'sc_bytes',
    'cs_bytes', 'time_taken'
]


def extract_logs(log_dir: pathlib.Path = LOG_DIRECTORY) -> pd.DataFrame:
    frames = []
    log_files = list(log_dir.glob('*.log'))
    logger.info('[Stage 1/4] Extracting + consolidating IIS log files')

    for f in log_files:
        rows = []
        with open(f, encoding='utf-8', errors='replace') as fh:
            for line in fh:
                line = line.strip()
                # Skip comment and header lines
                if not line or line.startswith('#'):
                    continue
                parts = line.split(' ')
                if len(parts) >= len(IIS_FIELDS):
                    rows.append(parts[:len(IIS_FIELDS)])
                elif len(parts) > 0:
                    # Pad short rows so we don't silently drop them
                    padded = parts + ['-'] * (len(IIS_FIELDS) - len(parts))
                    rows.append(padded)
        if rows:
            frames.append(pd.DataFrame(rows, columns=IIS_FIELDS))

    if frames:
        df = pd.concat(frames, ignore_index=True)
    else:
        df = pd.DataFrame(columns=IIS_FIELDS)

    # Normalise column names: replace hyphens with underscores
    df.columns = [c.replace('-', '_') for c in df.columns]

    df.to_csv(CONSOLIDATED_CSV, index=False)
    logger.info(f'  Consolidated {len(log_files)} log files -> {len(df)} rows -> {CONSOLIDATED_CSV.name}')
    return df