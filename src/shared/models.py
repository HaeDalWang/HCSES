"""
HCSES 공유 데이터 모델
EC-02: 절대값(_value, _level) vs 변동률(_pct, _ratio) 접미사 규칙 적용
"""
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class StockDailyRecord:
    ticker: str
    market: str                          # "KR" | "US"
    date: str                            # "YYYY-MM-DD"
    open_value: Optional[float] = None
    high_value: Optional[float] = None
    low_value: Optional[float] = None
    close_value: Optional[float] = None  # Adjusted Close
    volume_value: Optional[int] = None
    pbr_value: Optional[float] = None
    per_value: Optional[float] = None
    rsi_level: Optional[float] = None    # RSI(14) — 레벨 지표
    ma20_value: Optional[float] = None
    foreign_net_buy_value: Optional[float] = None   # KR only
    institution_net_buy_value: Optional[float] = None  # KR only
    data_status: str = "COLLECTING"      # COLLECTING | COMPLETE | FAILED
    analysis_status: str = "PENDING"     # PENDING | DONE
    collected_at: str = ""
    ttl: int = 0


@dataclass
class MarketIndicatorRecord:
    indicator: str                       # "VIX" | "US10Y" | "KRWUSD"
    date: str
    value_value: Optional[float] = None  # 지표 절대 수치
    prev_value: Optional[float] = None   # 전일 절대 수치
    change_pct: Optional[float] = None   # 전일 대비 변동률 (%)
    bb_upper_value: Optional[float] = None  # 볼린저 상단 (KRWUSD only)
    bb_lower_value: Optional[float] = None  # 볼린저 하단 (KRWUSD only)
    collected_at: str = ""
    ttl: int = 0


@dataclass
class TickerConfig:
    ticker: str
    market: str   # "KR" | "US"
    name: str
    enabled: bool = True


@dataclass
class StockStatsRecord:
    ticker: str
    stat_type: str                       # "PBR_STATS"
    pbr_min_value: Optional[float] = None
    pbr_max_value: Optional[float] = None
    pbr_median_value: Optional[float] = None
    years_of_data: Optional[int] = None
    updated_at: str = ""


@dataclass
class AnalysisResult:
    ticker: str
    market: str
    date: str
    valuation_score: float = 0.0
    momentum_score: float = 0.0
    supply_demand_score: float = 0.0
    total_score: float = 0.0
    kill_switch_active: bool = False
    kill_switch_reason: str = ""
    signals: list = field(default_factory=list)
    current_price_value: Optional[float] = None
    target_price_value: Optional[float] = None
    stop_loss_price_value: Optional[float] = None
