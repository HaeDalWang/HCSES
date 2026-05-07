"""
SwingAnalyzer Lambda 핸들러
Tier 2 단기 스윙 기회 포착 — 기존 DataCollector 데이터 Read-Only 사용
"""
import json
import logging
import os
from datetime import date, datetime, timedelta

import boto3

from src.swing_analyzer.tickers import SWING_TICKER_LIST, SWING_TICKER_NAMES
from src.swing_analyzer.swing_scoring import (
    calculate_swing_score,
    SWING_ALERT_THRESHOLD,
    MAX_DAILY_ALERTS,
)
from src.swing_analyzer.swing_service import (
    build_swing_context,
    load_vix_value,
    is_in_cooldown,
    record_cooldown,
    calc_exit_strategy,
)
from src.shared.market_calendar import is_within_market_hours, is_market_holiday
from src.shared.scoring import evaluate_kill_switch
from src.quant_analyzer.scoring_service import load_market_indicators

logging.getLogger().setLevel(logging.INFO)
logger = logging.getLogger(__name__)

ALERTING_ENGINE_ARN = os.environ.get("ALERTING_ENGINE_ARN", "")

_lambda_client = None


def _get_lambda_client():
    global _lambda_client
    if _lambda_client is None:
        _lambda_client = boto3.client("lambda", region_name=os.environ.get("AWS_REGION", "ap-northeast-2"))
    return _lambda_client


def _log(level: str, message: str, **kwargs) -> None:
    logger.log(
        getattr(logging, level.upper(), logging.INFO),
        json.dumps({"timestamp": datetime.utcnow().isoformat(), "level": level,
                    "message": message, **kwargs})
    )


def _format_price(value: float, market: str) -> str:
    if market == "KR":
        return f"{value:,.0f}"
    return f"{value:,.2f}"


def _pct_change(current: float, target: float) -> str:
    if current <= 0:
        return ""
    pct = (target - current) / current * 100
    sign = "+" if pct >= 0 else ""
    return f"{sign}{pct:.1f}%"


def _build_alert_payload(ctx, breakdown, exit_strategy, vix_value, market) -> dict:
    """AlertingEngine에 전달할 Tier 2 알림 payload."""
    currency = "₩" if market == "KR" else "$"
    close = ctx.close_value or 0
    target = exit_strategy["target_price_value"]
    stop = exit_strategy["stop_loss_value"]

    target_fmt = _format_price(target, market)
    stop_fmt = _format_price(stop, market)
    close_fmt = _format_price(close, market)
    atr_fmt = _format_price(ctx.atr_value, market) if ctx.atr_value else "N/A"

    ticker_name = SWING_TICKER_NAMES.get(ctx.ticker, ctx.ticker)
    title = f"{ticker_name} ({ctx.ticker})" if ticker_name != ctx.ticker else ctx.ticker

    # 시그널 텍스트
    t_score = breakdown.technical_rebound_score
    p_score = breakdown.price_support_score
    v_score = breakdown.volume_confirm_score

    t_label = breakdown.signals[0] if breakdown.signals else ""
    p_label = breakdown.signals[1] if len(breakdown.signals) > 1 else ""
    v_label = breakdown.signals[2] if len(breakdown.signals) > 2 else ""

    timecut_date = (date.fromisoformat(ctx.date) + timedelta(days=15)).isoformat()

    lines = [
        f"⚡ 단기 기회 | {title} | {market}",
        "",
        "━━━━━━━━ 진입 근거 ━━━━━━━━",
        f"현재가:         {currency}{close_fmt}",
        f"Swing Score:    {breakdown.total_score:.0f} / 100",
        f"  └ 기술반등:   {t_score:.0f} ({t_label})" if t_label else f"  └ 기술반등:   {t_score:.0f}",
        f"  └ 가격지지:   {p_score:.0f} ({p_label})" if p_label else f"  └ 가격지지:   {p_score:.0f}",
        f"  └ 거래량:     {v_score:.0f} ({v_label})" if v_label else f"  └ 거래량:     {v_score:.0f}",
        "",
        f"RSI:            {ctx.rsi_curr_level:.1f} (전일 {ctx.rsi_prev_level:.1f})" if ctx.rsi_curr_level and ctx.rsi_prev_level else "",
        f"MA5:            {currency}{_format_price(ctx.ma5_value, market)}" if ctx.ma5_value else "",
        f"MA20:           {currency}{_format_price(ctx.ma20_value, market)}" if ctx.ma20_value else "",
        "",
        "━━━━━━━━ 출구 전략 ━━━━━━━━",
        f"ATR(14):        {currency}{atr_fmt}",
        f"목표가:  {currency}{target_fmt}  → {_pct_change(close, target)}",
        f"손절가:  {currency}{stop_fmt}  (현재가 - 1.5×ATR) → {_pct_change(close, stop)}",
        f"타임컷:  15거래일 ({timecut_date})",
        "",
        "━━━━━━━━ 포지션 ━━━━━━━━",
        "종목당 한도:    총 예산의 5%",
        "최대 동시:      3종목",
        "",
        "━━━━━━━━ 시장 상태 ━━━━━━━━",
        f"VIX:     {vix_value:.1f}" if vix_value else "VIX:     N/A",
        f"{'⚠️ VIX 경고 구간 — 점수 30% 할인 적용됨' if breakdown.vix_penalty_applied else ''}",
        f"신호일:  {ctx.date}",
        "",
        "⚠️ 단기 스윙 목적 — 목표가 도달 시 즉시 청산 권장",
    ]

    message = "\n".join(line for line in lines if line is not None)
    return {"swing_alert_message": message, "ticker": ctx.ticker, "market": market}


def handler(event: dict, context) -> dict:
    """Lambda 진입점."""
    try:
        return _run(event, context)
    except Exception as e:
        _log("error", "unhandled_exception", error=str(e))
        return {"statusCode": 500, "body": "Internal error"}


def _run(event: dict, context) -> dict:
    market = event.get("market", os.environ.get("MARKET", "KR"))
    today = date.today()
    now = datetime.utcnow()

    # QA와 동일: 어제(최신 수집일) 데이터를 분석
    analysis_date = today - timedelta(days=1)
    while analysis_date.weekday() >= 5:
        analysis_date -= timedelta(days=1)

    # 시장 시간 검증
    if not is_within_market_hours(market, now):
        _log("info", "outside_market_hours", market=market)
        return {"statusCode": 200, "body": "outside_market_hours"}

    if is_market_holiday(market, analysis_date):
        _log("info", "market_holiday_skip", market=market, date=analysis_date.isoformat())
        return {"statusCode": 200, "body": "holiday_skip"}

    # Kill-Switch (Tier 1과 공유, 단 VIX 25~30은 Tier 2에서 패널티로 처리)
    indicators = load_market_indicators(analysis_date)
    kill_switch = evaluate_kill_switch(indicators)
    if kill_switch.active:
        # VIX 25~30 구간은 Tier 2에서 차단하지 않고 패널티만 적용
        if kill_switch.vix_value and 25 < kill_switch.vix_value <= 30:
            _log("warning", "vix_warning_tier2_continues", vix=kill_switch.vix_value)
        else:
            _log("warning", "kill_switch_active", reason=kill_switch.reason)
            return {"statusCode": 200, "body": f"kill_switch: {kill_switch.reason}"}

    vix_value = load_vix_value(analysis_date)

    tickers = SWING_TICKER_LIST.get(market, [])
    results = {"alerted": [], "analyzed": [], "skipped": [], "cooldown": []}
    alert_candidates = []

    for ticker in tickers:
        try:
            # 쿨다운 체크
            if is_in_cooldown(ticker, analysis_date):
                results["cooldown"].append(ticker)
                continue

            ctx = build_swing_context(ticker, market, analysis_date)
            if ctx is None:
                results["skipped"].append(ticker)
                continue

            breakdown = calculate_swing_score(ctx, vix_value)

            _log("info", "swing_analysis_complete", ticker=ticker, market=market,
                 total_score=breakdown.total_score, signals=breakdown.signals)

            if breakdown.total_score >= SWING_ALERT_THRESHOLD:
                if not ctx.close_value or ctx.close_value <= 0:
                    _log("warning", "invalid_close_value", ticker=ticker)
                    continue
                exit_strategy = calc_exit_strategy(
                    ctx.close_value, ctx.ma20_value, ctx.atr_value, market
                )
                alert_candidates.append({
                    "score": breakdown.total_score,
                    "ctx": ctx,
                    "breakdown": breakdown,
                    "exit_strategy": exit_strategy,
                })

            results["analyzed"].append(ticker)

        except Exception as e:
            _log("warning", "swing_analysis_failed", ticker=ticker, error=str(e))
            continue

    # 일일 알림 상한 (점수 높은 순 3개)
    alert_candidates.sort(key=lambda x: x["score"], reverse=True)
    alerts_sent = 0

    for candidate in alert_candidates[:MAX_DAILY_ALERTS]:
        ctx = candidate["ctx"]
        breakdown = candidate["breakdown"]
        exit_strategy = candidate["exit_strategy"]

        payload = _build_alert_payload(ctx, breakdown, exit_strategy, vix_value, market)

        success = _invoke_alerting_engine(payload)
        if success:
            record_cooldown(ctx.ticker, analysis_date)
            results["alerted"].append(ctx.ticker)
            alerts_sent += 1

    _log("info", "swing_run_complete", market=market, alerts_sent=alerts_sent, **results)
    return {"statusCode": 200, "body": json.dumps(results)}


def _invoke_alerting_engine(payload: dict) -> bool:
    """AlertingEngine Lambda 호출 (Tier 2 메시지 전달). 응답 검증 포함."""
    try:
        resp = _get_lambda_client().invoke(
            FunctionName=ALERTING_ENGINE_ARN,
            InvocationType="RequestResponse",
            Payload=json.dumps(payload).encode(),
        )
        result = json.loads(resp["Payload"].read())
        if result.get("statusCode") != 200:
            _log("error", "swing_alert_downstream_failed",
                 ticker=payload.get("ticker"), status=result.get("statusCode"))
            return False
        _log("info", "swing_alert_invoked", ticker=payload.get("ticker"))
        return True
    except Exception as e:
        _log("error", "swing_alert_invoke_failed", ticker=payload.get("ticker"), error=str(e))
        return False
