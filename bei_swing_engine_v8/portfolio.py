"""
Portfolio backtest module.
Backtests multiple tickers simultaneously with capital allocation,
position sizing, and portfolio-level metrics.
"""

import os
import time
import json
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime

import pandas as pd
import numpy as np

from .data import load_ohlcv
from .backtest import run_backtest, BacktestResult, Trade, compute_metrics
from .logging_config import get_logger

_log = get_logger("portfolio")


@dataclass
class PortfolioTrade:
    """A trade in the portfolio context."""
    ticker: str
    entry_date: pd.Timestamp
    exit_date: pd.Timestamp
    direction: str
    entry_price: float
    sl_price: float
    tp1_price: Optional[float]
    tp2_price: Optional[float]
    exit_price: float
    exit_reason: str
    r_multiple: float
    pnl_pct: float
    pnl_rpiah: float  # PnL in Rupiah
    allocated_capital: float


@dataclass
class TickerStats:
    """Per-ticker statistics in portfolio."""
    ticker: str
    total_trades: int = 0
    closed_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0
    expectancy: float = 0.0
    profit_factor: float = 0.0
    total_pnl: float = 0.0
    allocated_capital: float = 0.0
    return_pct: float = 0.0


@dataclass
class PortfolioResult:
    """Result of a portfolio backtest."""
    tickers: List[str] = field(default_factory=list)
    trades: List[PortfolioTrade] = field(default_factory=list)
    per_ticker: Dict[str, TickerStats] = field(default_factory=dict)
    equity_curve: List[Tuple[pd.Timestamp, float]] = field(default_factory=list)
    metrics: Dict = field(default_factory=dict)
    allocation_mode: str = "equal_weight"
    initial_capital: float = 10_000_000
    total_snapshots: int = 0


def run_portfolio_backtest(
    dataframes: List[pd.DataFrame],
    params: Dict,
    step: int = 1,
    allocation_mode: str = "equal_weight",
    initial_capital: Optional[float] = None,
) -> PortfolioResult:
    """
    Run portfolio backtest across multiple tickers.

    Args:
        dataframes: List of OHLCV DataFrames, one per ticker.
        params: Engine parameters dict.
        step: Backtest step (bars).
        allocation_mode: "equal_weight" or "risk_based".
        initial_capital: Total portfolio capital. Defaults to params["MODAL"].

    Returns:
        PortfolioResult with combined metrics.
    """
    if initial_capital is None:
        initial_capital = params.get("MODAL", 10_000_000)

    n_tickers = len(dataframes)
    if n_tickers == 0:
        return PortfolioResult(initial_capital=initial_capital)

    tickers = [df["Ticker"].iloc[0] for df in dataframes]
    _log.info("portfolio backtest start | tickers=%s capital=%d mode=%s",
              tickers, initial_capital, allocation_mode)

    # Capital allocation per ticker
    if allocation_mode == "equal_weight":
        capital_per_ticker = initial_capital / n_tickers
    elif allocation_mode == "risk_based":
        # Allocate based on inverse of ATR% (lower volatility = more capital)
        atr_pcts = {}
        for df in dataframes:
            from .indicators import compute_all_indicators
            inds = compute_all_indicators(df)
            atr_pct = inds["atr_pct"].iloc[-1]
            ticker = df["Ticker"].iloc[0]
            atr_pcts[ticker] = atr_pct if not pd.isna(atr_pct) else 3.0

        total_inv_atr = sum(1.0 / max(v, 0.5) for v in atr_pcts.values())
        capital_per_ticker = {}
        for df in dataframes:
            ticker = df["Ticker"].iloc[0]
            weight = (1.0 / max(atr_pcts.get(ticker, 3.0), 0.5)) / total_inv_atr
            capital_per_ticker[ticker] = initial_capital * weight
        # Use average for simpler handling
        capital_per_ticker_avg = initial_capital / n_tickers
    else:
        capital_per_ticker = initial_capital / n_tickers

    t_start = time.perf_counter()

    # Run individual backtests
    individual_results = []
    for df in dataframes:
        ticker = df["Ticker"].iloc[0]
        ticker_capital = initial_capital / n_tickers if allocation_mode == "equal_weight" else capital_per_ticker.get(ticker, initial_capital / n_tickers)

        # Override MODAL per ticker
        ticker_params = {**params, "MODAL": ticker_capital}

        result = run_backtest(df, ticker_params, step=step)
        individual_results.append((ticker, result, ticker_capital, df))

        _log.info("ticker done | %s trades=%d", ticker, len(result.trades))

    # Collect all trades with capital allocation
    all_trades = []
    for ticker, result, ticker_capital, df in individual_results:
        for trade in result.trades:
            # Scale PnL to allocated capital
            risk_pct = 0.01  # 1% risk per trade
            position_risk = ticker_capital * risk_pct
            risk_per_share = abs(trade.entry_price - trade.sl_price)
            if risk_per_share > 0:
                shares = int(position_risk / risk_per_share)
            else:
                shares = 0
            pnl_rpiah = shares * (trade.exit_price - trade.entry_price)

            ptrade = PortfolioTrade(
                ticker=ticker,
                entry_date=trade.entry_date,
                exit_date=trade.exit_date,
                direction=trade.direction,
                entry_price=trade.entry_price,
                sl_price=trade.sl_price,
                tp1_price=trade.tp1_price,
                tp2_price=trade.tp2_price,
                exit_price=trade.exit_price,
                exit_reason=trade.exit_reason,
                r_multiple=trade.r_multiple,
                pnl_pct=trade.pnl_pct,
                pnl_rpiah=pnl_rpiah,
                allocated_capital=ticker_capital,
            )
            all_trades.append(ptrade)

    # Sort trades by exit date
    all_trades.sort(key=lambda t: t.exit_date)

    # Build portfolio equity curve
    equity = initial_capital
    equity_curve = [(all_trades[0].entry_date, equity)] if all_trades else [(dataframes[0].index[0], equity)]
    for trade in all_trades:
        equity += trade.pnl_rpiah
        equity_curve.append((trade.exit_date, equity))

    # Per-ticker stats
    per_ticker = {}
    for ticker, result, ticker_capital, df in individual_results:
        ticker_trades = [t for t in all_trades if t.ticker == ticker]
        closed = [t for t in ticker_trades if t.exit_reason != "END"]
        wins = [t for t in closed if t.r_multiple > 0]
        losses = [t for t in closed if t.r_multiple <= 0]
        total_pnl = sum(t.pnl_rpiah for t in closed)

        stats = TickerStats(
            ticker=ticker,
            total_trades=len(ticker_trades),
            closed_trades=len(closed),
            winning_trades=len(wins),
            losing_trades=len(losses),
            win_rate=len(wins) / len(closed) * 100 if closed else 0,
            expectancy=np.mean([t.r_multiple for t in closed]) if closed else 0,
            profit_factor=sum(t.r_multiple for t in wins) / abs(sum(t.r_multiple for t in losses)) if losses and sum(t.r_multiple for t in losses) != 0 else 0,
            total_pnl=total_pnl,
            allocated_capital=ticker_capital,
            return_pct=total_pnl / ticker_capital * 100 if ticker_capital > 0 else 0,
        )
        per_ticker[ticker] = stats

    # Portfolio-level metrics
    closed_trades = [t for t in all_trades if t.exit_reason != "END"]
    wins = [t for t in closed_trades if t.r_multiple > 0]
    losses = [t for t in closed_trades if t.r_multiple <= 0]

    gross_profit = sum(t.r_multiple for t in wins)
    gross_loss = abs(sum(t.r_multiple for t in losses))
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0.0

    # Portfolio drawdown
    peak = initial_capital
    max_dd = 0.0
    for _, eq in equity_curve:
        if eq > peak:
            peak = eq
        dd = (peak - eq) / peak if peak > 0 else 0
        if dd > max_dd:
            max_dd = dd

    total_return = (equity - initial_capital) / initial_capital * 100

    # Sharpe-like ratio (simplified: mean / std of R-multiples)
    if len(closed_trades) > 1:
        r_values = [t.r_multiple for t in closed_trades]
        r_mean = np.mean(r_values)
        r_std = np.std(r_values)
        sharpe = r_mean / r_std if r_std > 0 else 0
    else:
        sharpe = 0

    total_snapshots = sum(len(r.snapshots) for _, r, _, _ in individual_results)

    metrics = {
        "total_trades": len(all_trades),
        "closed_trades": len(closed_trades),
        "open_at_end": len(all_trades) - len(closed_trades),
        "winning_trades": len(wins),
        "losing_trades": len(losses),
        "win_rate": len(wins) / len(closed_trades) * 100 if closed_trades else 0,
        "profit_factor": profit_factor,
        "avg_r_multiple": np.mean([t.r_multiple for t in closed_trades]) if closed_trades else 0,
        "expectancy": (len(wins) / len(closed_trades) * np.mean([t.r_multiple for t in wins]) - len(losses) / len(closed_trades) * abs(np.mean([t.r_multiple for t in losses]))) if closed_trades and wins and losses else 0,
        "max_drawdown_pct": max_dd * 100,
        "total_return_pct": total_return,
        "sharpe_ratio": sharpe,
        "initial_capital": initial_capital,
        "final_equity": equity,
        "n_tickers": n_tickers,
    }

    elapsed = time.perf_counter() - t_start
    _log.info("portfolio done | trades=%d return=%.2f%% max_dd=%.2f%% elapsed=%.1fs",
              len(all_trades), total_return, max_dd * 100, elapsed)

    return PortfolioResult(
        tickers=tickers,
        trades=all_trades,
        per_ticker=per_ticker,
        equity_curve=equity_curve,
        metrics=metrics,
        allocation_mode=allocation_mode,
        initial_capital=initial_capital,
        total_snapshots=total_snapshots,
    )


def render_portfolio_report(result: PortfolioResult) -> str:
    """Render portfolio backtest report as Markdown."""
    lines = []
    lines.append("# Portfolio Backtest Report")
    lines.append("")
    lines.append(f"**Tickers:** {', '.join(result.tickers)}")
    lines.append(f"**Allocation:** {result.allocation_mode}")
    lines.append(f"**Initial capital:** Rp {result.initial_capital:,.0f}".replace(",", "."))
    lines.append("")

    m = result.metrics
    lines.append("## Portfolio Metrics")
    lines.append("")
    col1 = [
        f"- **Total trades:** {m['total_trades']} (closed: {m['closed_trades']}, open: {m['open_at_end']})",
        f"- **Win rate:** {m['win_rate']:.1f}%",
        f"- **Expectancy:** {m['expectancy']:.2f}R",
        f"- **Profit factor:** {m['profit_factor']:.2f}",
    ]
    col2 = [
        f"- **Avg R-multiple:** {m['avg_r_multiple']:.2f}",
        f"- **Max drawdown:** {m['max_drawdown_pct']:.2f}%",
        f"- **Total return:** {m['total_return_pct']:.2f}%",
        f"- **Sharpe ratio:** {m['sharpe_ratio']:.2f}",
    ]
    for line in col1 + col2:
        lines.append(line)
    lines.append(f"- **Final equity:** Rp {m['final_equity']:,.0f}".replace(",", "."))
    lines.append("")

    # Per-ticker breakdown
    lines.append("## Per-Ticker Breakdown")
    lines.append("")
    lines.append("| Ticker | Trades | Win Rate | Expectancy | PF | PnL (Rp) | Return % | Allocated |")
    lines.append("|---|---|---|---|---|---|---|---|")
    for ticker in result.tickers:
        s = result.per_ticker.get(ticker)
        if s:
            lines.append(f"| {s.ticker} | {s.closed_trades} | {s.win_rate:.1f}% | "
                         f"{s.expectancy:.2f}R | {s.profit_factor:.2f} | "
                         f"Rp {s.total_pnl:,.0f} | {s.return_pct:.2f}% | "
                         f"Rp {s.allocated_capital:,.0f} |".replace(",", "."))
    lines.append("")

    # Trade log
    if result.trades:
        lines.append("## Trade Log")
        lines.append("")
        lines.append("| Ticker | Entry | Exit | Dir | Entry | SL | Exit | Reason | R | PnL(Rp) |")
        lines.append("|---|---|---|---|---|---|---|---|---|---|")
        for t in result.trades:
            lines.append(f"| {t.ticker} | {t.entry_date.strftime('%Y-%m-%d')} | "
                         f"{t.exit_date.strftime('%Y-%m-%d')} | {t.direction} | "
                         f"{t.entry_price:.0f} | {t.sl_price:.0f} | {t.exit_price:.0f} | "
                         f"{t.exit_reason} | {t.r_multiple:.2f} | "
                         f"Rp {t.pnl_rpiah:,.0f} |".replace(",", "."))
        lines.append("")

    lines.append("## Disclaimer")
    lines.append("")
    lines.append("> Hasil backtest berdasarkan data historis. Performa masa lalu tidak menjamin hasil masa depan.")
    lines.append("")

    return "\n".join(lines)


def plot_portfolio_equity(result: PortfolioResult):
    """Plot portfolio equity curve."""
    import plotly.graph_objects as go

    if not result.equity_curve:
        fig = go.Figure()
        fig.update_layout(title="No equity data")
        return fig

    dates = [e[0] for e in result.equity_curve]
    values = [e[1] for e in result.equity_curve]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=dates, y=values,
        mode="lines+markers", name="Portfolio Equity",
        line=dict(color="#1a5276", width=2),
        fill="tozeroy", fillcolor="rgba(26,82,118,0.1)",
    ))

    # Add initial capital line
    fig.add_hline(y=result.initial_capital, line_dash="dash", line_color="gray",
                  annotation_text=f"Initial: Rp {result.initial_capital:,.0f}".replace(",", "."))

    fig.update_layout(
        title="Portfolio Equity Curve",
        xaxis_title="Date", yaxis_title="Equity (Rp)",
        hovermode="x unified", template="plotly_white", height=400,
    )
    return fig


def plot_portfolio_drawdown(result: PortfolioResult):
    """Plot portfolio drawdown."""
    import plotly.graph_objects as go

    if not result.equity_curve:
        fig = go.Figure()
        fig.update_layout(title="No data")
        return fig

    dates = [e[0] for e in result.equity_curve]
    values = [e[1] for e in result.equity_curve]

    peak = values[0]
    drawdowns = []
    for v in values:
        if v > peak:
            peak = v
        dd = (peak - v) / peak * 100 if peak > 0 else 0
        drawdowns.append(dd)

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=dates, y=drawdowns,
        mode="lines", name="Drawdown %",
        line=dict(color="#e74c3c", width=2),
        fill="tozeroy", fillcolor="rgba(231,76,60,0.15)",
    ))
    fig.update_layout(
        title="Portfolio Drawdown", xaxis_title="Date",
        yaxis_title="Drawdown (%)", hovermode="x unified",
        template="plotly_white", height=300,
    )
    return fig


def plot_per_ticker_pnl(result: PortfolioResult):
    """Bar chart of PnL per ticker."""
    import plotly.graph_objects as go

    if not result.per_ticker:
        fig = go.Figure()
        fig.update_layout(title="No data")
        return fig

    tickers = list(result.per_ticker.keys())
    pnls = [result.per_ticker[t].total_pnl for t in tickers]
    colors = ["#27ae60" if p > 0 else "#e74c3c" for p in pnls]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=tickers, y=pnls, marker_color=colors, name="PnL (Rp)",
    ))
    fig.update_layout(
        title="PnL per Ticker", xaxis_title="Ticker",
        yaxis_title="PnL (Rp)", template="plotly_white", height=300,
    )
    return fig
