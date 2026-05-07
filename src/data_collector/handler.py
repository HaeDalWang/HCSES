"""
DataCollector Lambda 핸들러
Bulkhead 패턴, 전역 예외 처리 (SECURITY-15), 구조화 로깅 (SECURITY-03)
"""
import json
import logging
import os
import random
import time
from datetime import date, datetime

from src.data_collector.ingestion_service import (
    collect_stock_data,
    collect_kr_supply_demand,
    collect_market_indicators,
)
from src.shared import dynamodb_client as db
from src.shared.market_calendar import is_market_holiday

# 구조화 로깅 설정
logging.getLogger().setLevel(logging.INFO)
logger = logging.getLogger(__name__)

STOCK_DAILY_TABLE = os.environ.get("STOCK_DAILY_TABLE", "hcses-stock-daily")
MARKET_INDICATOR_TABLE = os.environ.get("MARKET_INDICATOR_TABLE", "hcses-market-indicator")

# 종목 목록 (실운영 시 DynamoDB 설정 테이블 또는 환경변수로 관리)
# Tier 1 + Tier 2 합집합 (DataCollector는 모든 대상 종목을 수집)
TICKER_LIST: dict[str, list[str]] = {
    "KR": [
        # Tier 1 (HCSES 밸류에이션)
        "005930.KS",  # 삼성전자
        "000660.KS",  # SK하이닉스
        "035420.KS",  # NAVER
        "005380.KS",  # 현대차
        "000270.KS",  # 기아
        "105560.KS",  # KB금융
        "010950.KS",  # S-Oil
        "329180.KS",  # HD현대중공업
        "005490.KS",  # POSCO홀딩스
        "033780.KS",  # KT&G
        "030200.KS",  # KT
        # Tier 2 전용 (Swing 고변동)
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
        # Tier 1 (HCSES 밸류에이션)
        "MU",     # Micron Technology
        "AMD",    # Advanced Micro Devices
        "INTC",   # Intel
        "QCOM",   # Qualcomm
        "AMAT",   # Applied Materials
        "LRCX",   # Lam Research
        "META",   # Meta Platforms
        "JPM",    # JPMorgan Chase
        "GS",     # Goldman Sachs
        "C",      # Citigroup
        "WFC",    # Wells Fargo
        "BAC",    # Bank of America
        "XOM",    # ExxonMobil
        "CVX",    # Chevron
        "OXY",    # Occidental Petroleum
        "DVN",    # Devon Energy
        "FCX",    # Freeport-McMoRan
        "NUE",    # Nucor
        "F",      # Ford
        "GM",     # General Motors
        "GE",     # GE Aerospace
        "CAT",    # Caterpillar
        "UNH",    # UnitedHealth Group
        "BMY",    # Bristol-Myers Squibb
        "T",      # AT&T
        # Tier 2 전용 (Swing 고변동)
        "NVDA",   # NVIDIA
        "TSLA",   # Tesla
        "SOFI",   # SoFi Technologies
        "COIN",   # Coinbase
        "ROKU",   # Roku
        "SNAP",   # Snap
        "RIVN",   # Rivian
        "MARA",   # Marathon Digital
        "PLTR",   # Palantir
        "SQ",     # Block
        "DKNG",   # DraftKings
        "SMCI",   # Super Micro Computer
        "CRWD",   # CrowdStrike
        "NET",    # Cloudflare
        "ARM",    # ARM Holdings
    ],
}

TICKER_NAMES: dict[str, str] = {
    # KR — Tier 1
    "005930.KS": "삼성전자",
    "000660.KS": "SK하이닉스",
    "035420.KS": "NAVER",
    "005380.KS": "현대차",
    "000270.KS": "기아",
    "105560.KS": "KB금융",
    "010950.KS": "S-Oil",
    "329180.KS": "HD현대중공업",
    "005490.KS": "POSCO홀딩스",
    "033780.KS": "KT&G",
    "030200.KS": "KT",
    # KR — Tier 2 전용
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
    # US — Tier 1
    "MU":    "Micron Technology",
    "AMD":   "Advanced Micro Devices",
    "INTC":  "Intel",
    "QCOM":  "Qualcomm",
    "AMAT":  "Applied Materials",
    "LRCX":  "Lam Research",
    "META":  "Meta Platforms",
    "JPM":   "JPMorgan Chase",
    "GS":    "Goldman Sachs",
    "C":     "Citigroup",
    "WFC":   "Wells Fargo",
    "BAC":   "Bank of America",
    "XOM":   "ExxonMobil",
    "CVX":   "Chevron",
    "OXY":   "Occidental Petroleum",
    "DVN":   "Devon Energy",
    "FCX":   "Freeport-McMoRan",
    "NUE":   "Nucor",
    "F":     "Ford",
    "GM":    "General Motors",
    "GE":    "GE Aerospace",
    "CAT":   "Caterpillar",
    "UNH":   "UnitedHealth Group",
    "BMY":   "Bristol-Myers Squibb",
    "T":     "AT&T",
    # US — Tier 2 전용
    "NVDA":  "NVIDIA",
    "TSLA":  "Tesla",
    "SOFI":  "SoFi Technologies",
    "COIN":  "Coinbase",
    "ROKU":  "Roku",
    "SNAP":  "Snap",
    "RIVN":  "Rivian",
    "MARA":  "Marathon Digital",
    "PLTR":  "Palantir",
    "SQ":    "Block",
    "DKNG":  "DraftKings",
    "SMCI":  "Super Micro Computer",
    "CRWD":  "CrowdStrike",
    "NET":   "Cloudflare",
    "ARM":   "ARM Holdings",
}


def _log(level: str, message: str, **kwargs) -> None:
    """SECURITY-03: 구조화 로그. 민감 데이터 절대 포함 금지."""
    logger.log(
        getattr(logging, level.upper(), logging.INFO),
        json.dumps({"timestamp": datetime.utcnow().isoformat(), "level": level,
                    "message": message, **kwargs})
    )


def handler(event: dict, context) -> dict:
    """Lambda 진입점. SECURITY-15: 전역 예외 처리."""
    try:
        return _run(event, context)
    except Exception as e:
        _log("error", "unhandled_exception", error=str(e))
        return {"statusCode": 500, "body": "Internal error"}


def _run(event: dict, context) -> dict:
    market = event.get("market", os.environ.get("MARKET", "KR"))
    today = date.today()
    correlation_id = getattr(context, "aws_request_id", "local")

    _log("info", "collection_start", market=market, date=today.isoformat(),
         correlation_id=correlation_id)

    # BR-05: 휴장일 체크
    if is_market_holiday(market, today):
        _log("info", "market_holiday_skip", market=market, date=today.isoformat())
        return {"statusCode": 200, "body": "holiday_skip"}

    tickers = TICKER_LIST.get(market, [])
    results = {"success": [], "failed": [], "skipped": []}

    for ticker in tickers:
        try:
            # 수집
            record = collect_stock_data(ticker, market, today)
            if record is None:
                results["skipped"].append(ticker)
                continue

            # KR 수급 데이터 병합
            if market == "KR":
                f_val, i_val = collect_kr_supply_demand(ticker, today)
                record.foreign_net_buy_value = f_val
                record.institution_net_buy_value = i_val

            # DynamoDB 저장 (TC-01 멱등성)
            record.data_status = "COMPLETE"
            saved = db.save_stock_daily(record, STOCK_DAILY_TABLE)
            if saved:
                results["success"].append(ticker)
                _log("info", "ticker_saved", ticker=ticker, market=market)
            else:
                results["failed"].append(ticker)

        except Exception as e:
            # Bulkhead: 단일 종목 실패 격리
            _log("warning", "ticker_collection_failed", ticker=ticker, error=str(e))
            try:
                db.update_data_status(ticker, today.isoformat(), "FAILED", STOCK_DAILY_TABLE)
            except Exception:
                pass
            results["failed"].append(ticker)

        # BR-04: Rate Limiting
        time.sleep(random.uniform(1, 3))

    # 시장 지표 수집
    try:
        indicators = collect_market_indicators(today)
        for ind in indicators:
            db.save_market_indicator(ind, MARKET_INDICATOR_TABLE)
        _log("info", "indicators_saved", count=len(indicators))
    except Exception as e:
        _log("error", "indicators_collection_failed", error=str(e))

    _log("info", "collection_complete", market=market, **results)
    return {"statusCode": 200, "body": json.dumps(results)}
