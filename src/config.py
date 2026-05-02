import os
import logging
import pathlib


# ── Paths ────────────────────────────────────────────────
BASE_DIR        = pathlib.Path(__file__).resolve().parent.parent
LOG_DIRECTORY   = pathlib.Path(os.getenv('LOG_DIRECTORY',  BASE_DIR / 'data' / 'sample'))
GEO_LITE_DB_PATH = pathlib.Path(os.getenv('GEO_LITE_DB_PATH', BASE_DIR / 'GeoLite2-City.mmdb'))


CONSOLIDATED_CSV = BASE_DIR / 'consolidated_iis_logs.csv'
STAGE2_CSV       = BASE_DIR / 'stage2.csv'
STAGE3_CSV       = BASE_DIR / 'stage3.csv'
DB_PATH          = BASE_DIR / os.getenv('DB_NAME', 'iis_web_log_warehouse.db')


# ── Logging ──────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s',
)
logger = logging.getLogger(__name__)
