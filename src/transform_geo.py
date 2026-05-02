import pandas as pd
import geoip2.database
from .config import CONSOLIDATED_CSV, STAGE2_CSV, GEO_LITE_DB_PATH, logger


def enrich_geo(df: pd.DataFrame = None) -> pd.DataFrame:
    if df is None: df = pd.read_csv(CONSOLIDATED_CSV)
    logger.info('[Stage 2/4] Enriching with GeoLite2 geolocation')
    if not GEO_LITE_DB_PATH.exists():
        logger.info('  GeoLite2 DB not found — skipping geo enrichment')
        for col in ['country','state_area','city','postcode','latitude','longitude']:
            df[col] = None
        df.to_csv(STAGE2_CSV, index=False); return df
    unique_ips = df['c_ip'].dropna().unique()
    logger.info(f'  Looking up {len(unique_ips)} unique IPs against GeoLite2')
    geo_rows = []
    with geoip2.database.Reader(str(GEO_LITE_DB_PATH)) as reader:
        for ip in unique_ips:
            try:
                r = reader.city(ip)
                geo_rows.append({'c_ip': ip,
                    'country': r.country.name, 'state_area': r.subdivisions.most_specific.name,
                    'city': r.city.name, 'postcode': r.postal.code,
                    'latitude': r.location.latitude, 'longitude': r.location.longitude})
            except Exception:
                geo_rows.append({'c_ip': ip, 'country': None, 'state_area': None,
                    'city': None, 'postcode': None, 'latitude': None, 'longitude': None})
    geo_df = pd.DataFrame(geo_rows)
    df = df.merge(geo_df, on='c_ip', how='left')
    df.to_csv(STAGE2_CSV, index=False)
    return df
