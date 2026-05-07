"""
Tier 2 Swing 대상 종목 리스트
선정 기준: 베타 > 1.3, 유동성 풍부, ATR/Close > 2.5%, 평균회귀 경향
"""

SWING_TICKER_LIST: dict[str, list[str]] = {
    "KR": [
        "005930.KS",  # 삼성전자
        "000660.KS",  # SK하이닉스
        "035420.KS",  # NAVER
        "005380.KS",  # 현대차
        "000270.KS",  # 기아
        "373220.KS",  # LG에너지솔루션
        "006400.KS",  # 삼성SDI
        "035720.KS",  # 카카오
        "247540.KS",  # 에코프로비엠
        "086520.KS",  # 에코프로
        "003670.KS",  # 포스코퓨처엠
        "042700.KS",  # 한미반도체
        "012330.KS",  # 현대모비스
        "034730.KS",  # SK
        "028260.KS",  # 삼성물산
    ],
    "US": [
        "NVDA",   # NVIDIA
        "TSLA",   # Tesla
        "AMD",    # Advanced Micro Devices
        "MU",     # Micron Technology
        "SOFI",   # SoFi Technologies
        "COIN",   # Coinbase
        "ROKU",   # Roku
        "SNAP",   # Snap
        "RIVN",   # Rivian
        "MARA",   # Marathon Digital
        "PLTR",   # Palantir
        "SQ",     # Block (Square)
        "DKNG",   # DraftKings
        "FCX",    # Freeport-McMoRan
        "XOM",    # ExxonMobil
        "BAC",    # Bank of America
        "SMCI",   # Super Micro Computer
        "CRWD",   # CrowdStrike
        "NET",    # Cloudflare
        "ARM",    # ARM Holdings
    ],
}

SWING_TICKER_NAMES: dict[str, str] = {
    # KR
    "005930.KS": "삼성전자",
    "000660.KS": "SK하이닉스",
    "035420.KS": "NAVER",
    "005380.KS": "현대차",
    "000270.KS": "기아",
    "373220.KS": "LG에너지솔루션",
    "006400.KS": "삼성SDI",
    "035720.KS": "카카오",
    "247540.KS": "에코프로비엠",
    "086520.KS": "에코프로",
    "003670.KS": "포스코퓨처엠",
    "042700.KS": "한미반도체",
    "012330.KS": "현대모비스",
    "034730.KS": "SK",
    "028260.KS": "삼성물산",
    # US
    "NVDA": "NVIDIA",
    "TSLA": "Tesla",
    "AMD": "Advanced Micro Devices",
    "MU": "Micron Technology",
    "SOFI": "SoFi Technologies",
    "COIN": "Coinbase",
    "ROKU": "Roku",
    "SNAP": "Snap",
    "RIVN": "Rivian",
    "MARA": "Marathon Digital",
    "PLTR": "Palantir",
    "SQ": "Block",
    "DKNG": "DraftKings",
    "FCX": "Freeport-McMoRan",
    "XOM": "ExxonMobil",
    "BAC": "Bank of America",
    "SMCI": "Super Micro Computer",
    "CRWD": "CrowdStrike",
    "NET": "Cloudflare",
    "ARM": "ARM Holdings",
}
