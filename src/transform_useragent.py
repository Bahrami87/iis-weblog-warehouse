import pandas as pd
from user_agents import parse as ua_parse
from .config import STAGE2_CSV, STAGE3_CSV, logger

# Known bot/crawler UA keywords
BOT_KEYWORDS = [
    'bot', 'crawler', 'spider', 'slurp', 'baidu', 'yandex',
    'bingbot', 'googlebot', 'msnbot', 'wget', 'curl', 'python',
    'scrapy', 'archiver', 'scan', 'zgrab'
]

def parse_user_agents(df: pd.DataFrame = None) -> pd.DataFrame:
    if df is None:
        df = pd.read_csv(STAGE2_CSV)
    logger.info('[Stage 3/4] Parsing User-Agent + crawler detection')

    # Crawler detection: IPs that requested robots.txt
    crawler_ips = set(
        df.loc[df['cs_uri_stem'].str.contains('robots.txt', na=False), 'c_ip']
    )

    # Also flag by UA string keywords (more reliable than IP alone)
    def is_bot_ua(ua_str):
        if not ua_str or ua_str == '-':
            return False
        ua_lower = ua_str.lower()
        return any(kw in ua_lower for kw in BOT_KEYWORDS)

    logger.info(f'  Identified {len(crawler_ips)} crawler IPs')

    # Parse only unique UA strings
    unique_uas = df['cs_user_agent'].dropna().unique()
    unique_uas = [u for u in unique_uas if u != '-']
    logger.info(f'  Parsed {len(unique_uas)} unique User-Agent strings')

    ua_rows = []
    for ua_str in unique_uas:
        ua = ua_parse(ua_str.replace('+', ' '))
        # Is_Crawler: UA-keyword match OR IP requested robots.txt
        # We store per-UA bot flag here; IP-based flag applied at row level
        bot_by_ua = is_bot_ua(ua_str)
        ua_rows.append({
            'cs_user_agent': ua_str,
            'browser_name': ua.browser.family,
            'browser_version': ua.browser.version_string,
            'operating_system': ua.os.family,
            'os_version': ua.os.version_string,
            'bot_by_ua': bot_by_ua,
        })

    ua_df = pd.DataFrame(ua_rows)
    df = df.merge(ua_df, on='cs_user_agent', how='left')

    # Final is_crawler: bot by UA string OR IP requested robots.txt
    df['is_crawler'] = (
        df['bot_by_ua'].fillna(False) |
        df['c_ip'].isin(crawler_ips)
    )
    df.drop(columns=['bot_by_ua'], inplace=True)

    df.to_csv(STAGE3_CSV, index=False)
    return df