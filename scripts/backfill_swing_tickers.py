"""
Tier 2 신규 종목 과거 30거래일 데이터 백필 스크립트
기존 DataCollector 수집 로직을 재사용하여 StockDailyTable에 삽입.
실행: python3 scripts/backfill_swing_tickers.py
"""
import sys
import os
import time
import random
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("AWS_REGION", "ap-northeast-2")
os.environ.setdefault("AWS_PROFILE", "default")
os.environ.setdefault("AWS_DEFAULT_PROFILE", "default")

import boto3
# 프로필을 명시적으로 지정하여 DynamoDB 연결
_session = boto3.Session(profile_name="default", region_name="ap-northeast-2")

from src.data_collector.ingestion_service import collect_stock_data, collect_kr_supply_demand
from src.shared import dynamodb_client as db

# 기존 get_dynamodb()를 default 프로필 세션으로 오버라이드
db._dynamodb = _session.resource("dynamodb", region_name="ap-northeast-2")

STOCK_DAILY_TABLE = "hcses-stock-daily"

# Tier 2 전용 종목 (기존 Tier 1에 없는 것만)
NEW_TICKERS_KR = [
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
]

NEW_TICKERS_US = [
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
]

BACKFILL_DAYS = 35  # 30거래일 + 주말/공휴일 버퍼


def get_trading_days(market: str, days: int) -> list[date]:
    """과거 N 캘린더일 중 평일만 반환."""
    today = date.today()
    result = []
    for i in range(1, days + 1):
        d = today - timedelta(days=i)
        if d.weekday() < 5:
            result.append(d)
    return sorted(result)


def backfill_ticker(ticker: str, market: str, trading_days: list[date]) -> dict:
    """단일 종목 백필. 이미 존재하는 날짜는 멱등성으로 스킵."""
    stats = {"success": 0, "skipped": 0, "failed": 0}

    for target_date in trading_days:
        try:
            record = collect_stock_data(ticker, market, target_date)
            if record is None:
                stats["skipped"] += 1
                continue

            if market == "KR":
                f_val, i_val = collect_kr_supply_demand(ticker, target_date)
                record.foreign_net_buy_value = f_val
                record.institution_net_buy_value = i_val

            record.data_status = "COMPLETE"
            record.analysis_status = "DONE"  # 백필 데이터는 분석 불필요
            saved = db.save_stock_daily(record, STOCK_DAILY_TABLE)
            if saved:
                stats["success"] += 1
            else:
                stats["failed"] += 1

        except Exception as e:
            print(f"  ERROR {ticker} {target_date}: {e}")
            stats["failed"] += 1

        time.sleep(random.uniform(0.5, 1.5))

    return stats


def main():
    print("=== Tier 2 신규 종목 백필 시작 ===\n")

    kr_days = get_trading_days("KR", BACKFILL_DAYS)
    us_days = get_trading_days("US", BACKFILL_DAYS)
    print(f"KR 거래일: {len(kr_days)}일 ({kr_days[0]} ~ {kr_days[-1]})")
    print(f"US 거래일: {len(us_days)}일 ({us_days[0]} ~ {us_days[-1]})\n")

    total_stats = {"success": 0, "skipped": 0, "failed": 0}

    print("--- US 종목 백필 ---")
    for ticker in NEW_TICKERS_US:
        stats = backfill_ticker(ticker, "US", us_days)
        print(f"  {ticker:6s} → success={stats['success']} skipped={stats['skipped']} failed={stats['failed']}")
        for k in total_stats:
            total_stats[k] += stats[k]
        time.sleep(random.uniform(2, 4))

    print("\n--- KR 종목 백필 ---")
    for ticker in NEW_TICKERS_KR:
        stats = backfill_ticker(ticker, "KR", kr_days)
        print(f"  {ticker:12s} → success={stats['success']} skipped={stats['skipped']} failed={stats['failed']}")
        for k in total_stats:
            total_stats[k] += stats[k]
        time.sleep(random.uniform(2, 4))

    print(f"\n=== 백필 완료 ===")
    print(f"총 success={total_stats['success']} skipped={total_stats['skipped']} failed={total_stats['failed']}")


if __name__ == "__main__":
    main()
