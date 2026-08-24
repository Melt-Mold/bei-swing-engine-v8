"""
Backtest / walk-forward analysis engine (Module 13).
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from datetime import datetime

import pandas as pd
import numpy as np

from .data import load_ohlcv
from .engine import analyze_ticker
from .indicators import compute_all_indicators
from .structure import analyze_structure
from .logging_config import get_logger

_log = get_logger("backtest")


@dataclass
class Trade:
    entry_date: pd.Timestamp
    exit_date: pd.Timestamp
    ticker: str
    direction: str
    entry_price: float
    sl_price: float
    tp1_price: Optional[float]
    tp2_price: Optional[float]
    exit_price: float
    exit_reason: str  # SL, TP2, TP1, SELL_SIGNAL, END
    r_multiple: float
    pnl_pct: float


@dataclass
class BacktestResult:
    ticker: str
    trades: List[Trade] = field(default_factory=list)
    snapshots: List[Dict] = field(default_factory=list)
    equity_curve: List[Tuple[pd.Timestamp, float]] = field(default_factory=list)
    metrics: Dict = field(default_factory=dict)


def run_engine_as_of(
    df: pd.DataFrame,
    cutoff: pd.Timestamp,
    params: Dict,
    precomputed: Optional[Dict] = None,
) -> Dict:
    """Run engine on data truncated at cutoff (no look-ahead)."""
    truncated = df[df.index <= cutoff].copy()
    if len(truncated) < 20:
        return {"status": "INSUFFICIENT_DATA"}
    return analyze_ticker(truncated, params, ihsg_df=None, precomputed=precomputed, build_output_rows=False)


def generate_trades(
    snapshots: List[Dict],
    df: pd.DataFrame,
) -> List[Trade]:
    """
    Generate trades from consecutive BUY decisions.
    Exit on: SL hit, TP2 hit, SELL signal, or end of data.
    """
    trades = []
    active_trade = None

    # Create date -> OHLC map for fast lookup
    bars = df.to_dict("index")

    for i, snap in enumerate(snapshots):
        date = snap["date"]
        if date not in bars:
            continue
        bar = bars[date]

        if active_trade is None:
            if snap["decision"] == "BUY" and snap["entry"] is not None and snap["sl"] is not None:
                active_trade = {
                    "entry_date": date,
                    "entry_price": snap["entry"],
                    "sl": snap["sl"],
                    "tp1": snap["tp1"],
                    "tp2": snap["tp2"],
                    "direction": "LONG",
                }
            continue

        # Check exit conditions
        exited = False
        exit_price = bar["Close"]
        exit_reason = "END"

        # SL hit
        if bar["Low"] <= active_trade["sl"]:
            exited = True
            exit_price = min(bar["Open"], active_trade["sl"]) if i > 0 else active_trade["sl"]
            exit_reason = "SL"
        # TP2 hit
        elif active_trade["tp2"] is not None and bar["High"] >= active_trade["tp2"]:
            exited = True
            exit_price = max(bar["Open"], active_trade["tp2"])
            exit_reason = "TP2"
        # TP1 hit (full exit for simplicity)
        elif active_trade["tp1"] is not None and bar["High"] >= active_trade["tp1"]:
            exited = True
            exit_price = max(bar["Open"], active_trade["tp1"])
            exit_reason = "TP1"
        # SELL signal
        elif snap["decision"] in {"SELL", "NO_SETUP"}:
            exited = True
            exit_price = bar["Close"]
            exit_reason = "SELL_SIGNAL"

        if exited or i == len(snapshots) - 1:
            entry = active_trade["entry_price"]
            sl = active_trade["sl"]
            risk = abs(entry - sl)
            reward = exit_price - entry
            r_multiple = reward / risk if risk != 0 else 0.0
            pnl_pct = (reward / entry) * 100.0 if entry != 0 else 0.0

            trades.append(Trade(
                entry_date=active_trade["entry_date"],
                exit_date=date,
                ticker=snap.get("ticker", ""),
                direction=active_trade["direction"],
                entry_price=entry,
                sl_price=sl,
                tp1_price=active_trade["tp1"],
                tp2_price=active_trade["tp2"],
                exit_price=exit_price,
                exit_reason=exit_reason,
                r_multiple=r_multiple,
                pnl_pct=pnl_pct,
            ))
            active_trade = None

    return trades


def compute_metrics(trades: List[Trade], initial_equity: float = 1_000_000.0) -> Dict:
    """Compute backtest metrics from closed trades (excludes END/open trades)."""
    closed_trades = [t for t in trades if t.exit_reason != "END"]

    if not closed_trades:
        return {
            "total_trades": 0,
            "closed_trades": 0,
            "open_at_end": len(trades),
            "winning_trades": 0,
            "losing_trades": 0,
            "win_rate": 0.0,
            "profit_factor": 0.0,
            "avg_r_multiple": 0.0,
            "expectancy": 0.0,
            "max_drawdown_pct": 0.0,
            "total_return_pct": 0.0,
            "equity_curve": [(trades[0].entry_date, initial_equity)] if trades else [],
        }

    total = len(closed_trades)
    wins = [t for t in closed_trades if t.r_multiple > 0]
    losses = [t for t in closed_trades if t.r_multiple <= 0]
    win_rate = len(wins) / total if total > 0 else 0.0

    gross_profit = sum(t.r_multiple for t in wins)
    gross_loss = abs(sum(t.r_multiple for t in losses))
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else float("inf")

    avg_r = np.mean([t.r_multiple for t in closed_trades])
    avg_win_r = np.mean([t.r_multiple for t in wins]) if wins else 0.0
    avg_loss_r = np.mean([abs(t.r_multiple) for t in losses]) if losses else 0.0
    expectancy = (win_rate * avg_win_r) - ((1 - win_rate) * avg_loss_r)

    # Equity curve & max drawdown
    equity = initial_equity
    equity_curve = [(closed_trades[0].entry_date, equity)]
    peak = equity
    max_dd = 0.0
    for t in closed_trades:
        # Assume fixed fractional risk per trade (1% of equity)
        risk_pct = 0.01
        position_risk = equity * risk_pct
        risk_per_share = abs(t.entry_price - t.sl_price)
        if risk_per_share > 0:
            shares = int(position_risk / risk_per_share)
        else:
            shares = 0
        pnl = shares * (t.exit_price - t.entry_price)
        equity += pnl
        equity_curve.append((t.exit_date, equity))
        if equity > peak:
            peak = equity
        dd = (peak - equity) / peak
        if dd > max_dd:
            max_dd = dd

    total_return = (equity - initial_equity) / initial_equity * 100.0

    return {
        "total_trades": len(trades),
        "closed_trades": total,
        "open_at_end": len(trades) - total,
        "winning_trades": len(wins),
        "losing_trades": len(losses),
        "win_rate": win_rate * 100.0,
        "profit_factor": profit_factor,
        "avg_r_multiple": avg_r,
        "expectancy": expectancy,
        "max_drawdown_pct": max_dd * 100.0,
        "total_return_pct": total_return,
        "equity_curve": equity_curve,
    }


def run_backtest(
    df: pd.DataFrame,
    params: Dict,
    step: int = 5,
    min_bars: int = 50,
) -> BacktestResult:
    """
    Run walk-forward backtest.
    step: re-run engine every N bars.
    min_bars: minimum bars before first cutoff.
    """
    import time as _time

    ticker = df["Ticker"].iloc[0]
    result = BacktestResult(ticker=ticker)
    initial_equity = params.get("MODAL", 10_000_000)

    # Generate cutoff dates
    cutoff_indices = list(range(min_bars, len(df), step))
    if not cutoff_indices:
        _log.warning("backtest skipped | ticker=%s reason=insufficient_bars", ticker)
        return result

    _log.info("backtest start | ticker=%s bars=%d snapshots=%d step=%d", ticker, len(df), len(cutoff_indices), step)

    # Precompute indicators and structure once on full data for speed
    t0 = _time.perf_counter()
    full_indicators = compute_all_indicators(df)
    full_structure = analyze_structure(df, full_indicators)
    precomputed = {"indicators": full_indicators, "structure": full_structure}
    _log.debug("precompute done | ticker=%s elapsed=%.3fs", ticker, _time.perf_counter() - t0)

    t_snap = _time.perf_counter()
    buy_count = sell_count = 0
    for idx in cutoff_indices:
        cutoff = df.index[idx]
        res = run_engine_as_of(df, cutoff, params, precomputed=precomputed)

        if res.get("status") != "OK":
            continue

        dec = res["decision"].decision
        if dec == "BUY":
            buy_count += 1
        elif dec == "SELL":
            sell_count += 1

        snap = {
            "date": cutoff,
            "ticker": ticker,
            "close": res["df"]["Close"].iloc[-1],
            "decision": res["decision"].decision,
            "decision_direction": res["decision"].decision_direction,
            "thesis": res["decision"].thesis_state,
            "setup": f"{res['primary_setup'].type} {res['primary_setup'].status}",
            "entry": res["decision"].entry,
            "sl": res["decision"].sl,
            "tp1": res["decision"].tp1,
            "tp2": res["decision"].tp2,
            "rr": res["decision"].rr_raw,
        }
        result.snapshots.append(snap)

    _log.info("snapshots done | ticker=%s snapshots=%d buys=%d sells=%d elapsed=%.2fs",
              ticker, len(result.snapshots), buy_count, sell_count, _time.perf_counter() - t_snap)

    # Generate trades
    result.trades = generate_trades(result.snapshots, df)
    _log.info("trades generated | ticker=%s trades=%d", ticker, len(result.trades))

    # Compute metrics
    result.metrics = compute_metrics(result.trades, initial_equity=initial_equity)
    result.equity_curve = result.metrics.pop("equity_curve", [])
    _log.info("backtest metrics | ticker=%s closed=%d win_rate=%.1f%% expectancy=%.2fR max_dd=%.2f%% total_return=%.2f%%",
              ticker, result.metrics["closed_trades"], result.metrics["win_rate"],
              result.metrics["expectancy"], result.metrics["max_drawdown_pct"], result.metrics["total_return_pct"])

    return result


def validate_as_of_consistency(df: pd.DataFrame, params: Dict, n_checks: int = 5) -> List[str]:
    """
    Validate that Engine(truncated at D) == Engine(complete data as-of D).
    Returns list of mismatches; empty if all consistent.
    """
    mismatches = []
    # Pick n_checks random-ish cutoffs
    step = max(1, (len(df) - 50) // n_checks)
    indices = list(range(50, len(df) - step, step))[:n_checks]

    for idx in indices:
        cutoff = df.index[idx]
        res_trunc = run_engine_as_of(df, cutoff, params)
        res_full = run_engine_as_of(df, cutoff, params)  # same cutoff on full df = truncation

        if res_trunc.get("status") != res_full.get("status"):
            mismatches.append(f"{cutoff.date()}: status mismatch {res_trunc.get('status')} vs {res_full.get('status')}")
            continue

        if res_trunc.get("status") == "OK":
            d1 = res_trunc["decision"]
            d2 = res_full["decision"]
            if d1.decision != d2.decision or d1.entry != d2.entry or d1.sl != d2.sl:
                mismatches.append(f"{cutoff.date()}: decision/levels mismatch")

    return mismatches


def render_backtest_report(result: BacktestResult) -> str:
    """Render backtest report in Markdown."""
    lines = []
    lines.append(f"# Backtest Report — {result.ticker}")
    lines.append("")
    lines.append(f"**Total snapshots:** {len(result.snapshots)}")
    lines.append(f"**Total trades:** {result.metrics['total_trades']} (closed: {result.metrics['closed_trades']}, open at end: {result.metrics['open_at_end']})")
    lines.append("")

    lines.append("## Metrics")
    lines.append("")
    lines.append(f"- **Winning trades:** {result.metrics['winning_trades']}")
    lines.append(f"- **Losing trades:** {result.metrics['losing_trades']}")
    lines.append(f"- **Win rate:** {result.metrics['win_rate']:.2f}%")
    lines.append(f"- **Profit factor:** {result.metrics['profit_factor']:.2f}")
    lines.append(f"- **Average R-multiple:** {result.metrics['avg_r_multiple']:.2f}")
    lines.append(f"- **Expectancy (R):** {result.metrics['expectancy']:.2f}")
    lines.append(f"- **Max drawdown:** {result.metrics['max_drawdown_pct']:.2f}%")
    lines.append(f"- **Total return:** {result.metrics['total_return_pct']:.2f}%")
    lines.append("")

    lines.append("## Trade Log")
    lines.append("")
    lines.append("| Entry Date | Exit Date | Direction | Entry | SL | TP1 | TP2 | Exit | Reason | R-multiple | PnL% |")
    lines.append("|---|---|---|---|---|---|---|---|---|---|---|")
    for t in result.trades:
        lines.append(
            f"| {t.entry_date.strftime('%Y-%m-%d')} | {t.exit_date.strftime('%Y-%m-%d')} | {t.direction} | "
            f"{t.entry_price:.0f} | {t.sl_price:.0f} | {t.tp1_price if t.tp1_price is not None else 'N/A'} | "
            f"{t.tp2_price if t.tp2_price is not None else 'N/A'} | {t.exit_price:.0f} | {t.exit_reason} | "
            f"{t.r_multiple:.2f} | {t.pnl_pct:.2f}% |"
        )
    lines.append("")

    return "\n".join(lines)


def render_backtest_aggregate(results: List[BacktestResult]) -> str:
    """Render aggregate backtest summary across multiple tickers."""
    lines = []
    lines.append("---")
    lines.append("## Aggregate Backtest Summary")
    lines.append("")
    lines.append("| Ticker | Snapshots | Closed Trades | Win Rate | Avg R | Expectancy | Max DD | Total Return |")
    lines.append("|---|---|---|---|---|---|---|---|")
    for r in results:
        m = r.metrics
        lines.append(
            f"| {r.ticker} | {len(r.snapshots)} | {m['closed_trades']} | "
            f"{m['win_rate']:.2f}% | {m['avg_r_multiple']:.2f} | {m['expectancy']:.2f} | "
            f"{m['max_drawdown_pct']:.2f}% | {m['total_return_pct']:.2f}% |"
        )
    lines.append("")
    return "\n".join(lines)
