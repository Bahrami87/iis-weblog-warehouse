import pandas as pd
from user_agents import parse as ua_parse
from .config import STAGE2_CSV, STAGE3_CSV, logger


def parse_user_agents(df: pd.DataFrame = None) -> pd.DataFrame:
    if df is None: df = pd.read_csv(STAGE2_CSV)
    logger.info('[Stage 3/4] Parsing User-Agent + crawler detection')
    # Crawler detection: IPs that ever requested robots.txt
    crawler_ips = set(df.loc[df['cs_uri_stem'].str.contains('robots.txt', na=False), 'c_ip'])
    df['is_crawler'] = df['c_ip'].isin(crawler_ips)
    logger.info(f'  Identified {len(crawler_ips)} crawler IPs')
    # Parse only unique UA strings
    unique_uas = df['cs_user_agent'].dropna().unique()
    logger.info(f'  Parsed {len(unique_uas)} unique User-Agent strings')
    ua_rows = []
    for ua_str in unique_uas:
        ua = ua_parse(ua_str.replace('+', ' '))
        ua_rows.append({'cs_user_agent': ua_str, 'browser_name': ua.browser.family,
            'browser_version': ua.browser.version_string,
            'operating_system': ua.os.family, 'os_version': ua.os.version_string})
    ua_df = pd.DataFrame(ua_rows)
    df = df.merge(ua_df, on='cs_user_agent', how='left')
    df.to_csv(STAGE3_CSV, index=False)
    return df
