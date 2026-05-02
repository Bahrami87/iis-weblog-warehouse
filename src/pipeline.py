import argparse
import time
from .config import logger
from .extract import extract_logs
from .transform_geo import enrich_geo
from .transform_useragent import parse_user_agents
from .load_warehouse import load_warehouse


def main():
    ap = argparse.ArgumentParser(description="IIS Web-Log Warehouse Pipeline")
    ap.add_argument('--skip-extract', action='store_true')
    ap.add_argument('--skip-geo',     action='store_true')
    ap.add_argument('--skip-ua',      action='store_true')
    ap.add_argument('--skip-load',    action='store_true')
    args = ap.parse_args()

    t0 = time.time()
    df = extract_logs()        if not args.skip_extract else None
    df = enrich_geo(df)        if not args.skip_geo     else None
    df = parse_user_agents(df) if not args.skip_ua      else None
    if not args.skip_load:
        load_warehouse(df)
    logger.info(f'Pipeline finished in {time.time() - t0:.1f} s')


main()