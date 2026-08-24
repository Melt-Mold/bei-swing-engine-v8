"""
Chart visualization module using Plotly.
Generates interactive charts for backtest results:
- Equity curve
- Price chart with trade markers
- Drawdown chart
"""

from typing import List, Dict, Tuple, Optional
import pandas as pd
import numpy as np

from .backtest import BacktestResult, Trade


def plot_equity_curve(equity_curve: List[Tuple]) -> "plotly.graph_objects.Figure":
    """
    Plot equity curve from backtest result.
    equity_curve: list of (date, equity_value) tuples.
    """
    import plotly.graph_objects as go

    if not equity_curve:
        fig = go.Figure()
        fig.update_layout(title="No equity data available")
        return fig

    dates = [e[0] for e in equity_curve]
    values = [e[1] for e in equity_curve]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=dates,
        y=values,
        mode="lines+markers",
        name="Equity",
        line=dict(color="#2874a6", width=2),
        marker=dict(size=5),
        fill="tozeroy",
        fillcolor="rgba(40,116,166,0.1)",
    ))

    fig.update_layout(
        title="Equity Curve",
        xaxis_title="Date",
        yaxis_title="Equity (Rp)",
        hovermode="x unified",
        template="plotly_white",
        height=400,
    )

    return fig


def plot_price_with_trades(df: pd.DataFrame, trades: List[Trade]) -> "plotly.graph_objects.Figure":
    """
    Plot price chart (candlestick or line) with trade entry/exit markers.
    """
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots

    if df.empty:
        fig = go.Figure()
        fig.update_layout(title="No price data available")
        return fig

    fig = go.Figure()

    # Price line
    fig.add_trace(go.Scatter(
        x=df.index,
        y=df["Close"],
        mode="lines",
        name="Close Price",
        line=dict(color="#2c3e50", width=1.5),
    ))

    # Trade markers
    if trades:
        entry_dates = [t.entry_date for t in trades]
        entry_prices = [t.entry_price for t in trades]
        exit_dates = [t.exit_date for t in trades]
        exit_prices = [t.exit_price for t in trades]

        # Entry markers (green triangle up for LONG, red triangle down for SHORT)
        long_entries = [(t.entry_date, t.entry_price) for t in trades if t.direction == "LONG"]
        short_entries = [(t.entry_date, t.entry_price) for t in trades if t.direction == "SHORT"]

        if long_entries:
            fig.add_trace(go.Scatter(
                x=[e[0] for e in long_entries],
                y=[e[1] for e in long_entries],
                mode="markers",
                name="LONG Entry",
                marker=dict(symbol="triangle-up", size=12, color="#27ae60"),
            ))

        if short_entries:
            fig.add_trace(go.Scatter(
                x=[e[0] for e in short_entries],
                y=[e[1] for e in short_entries],
                mode="markers",
                name="SHORT Entry",
                marker=dict(symbol="triangle-down", size=12, color="#e74c3c"),
            ))

        # Exit markers (color by reason)
        sl_exits = [(t.exit_date, t.exit_price) for t in trades if t.exit_reason == "SL"]
        tp_exits = [(t.exit_date, t.exit_price) for t in trades if t.exit_reason in ("TP1", "TP2")]
        sell_exits = [(t.exit_date, t.exit_price) for t in trades if t.exit_reason == "SELL_SIGNAL"]
        end_exits = [(t.exit_date, t.exit_price) for t in trades if t.exit_reason == "END"]

        if sl_exits:
            fig.add_trace(go.Scatter(
                x=[e[0] for e in sl_exits],
                y=[e[1] for e in sl_exits],
                mode="markers",
                name="SL Exit",
                marker=dict(symbol="x", size=10, color="#e74c3c"),
            ))

        if tp_exits:
            fig.add_trace(go.Scatter(
                x=[e[0] for e in tp_exits],
                y=[e[1] for e in tp_exits],
                mode="markers",
                name="TP Exit",
                marker=dict(symbol="star", size=12, color="#27ae60"),
            ))

        if sell_exits:
            fig.add_trace(go.Scatter(
                x=[e[0] for e in sell_exits],
                y=[e[1] for e in sell_exits],
                mode="markers",
                name="SELL Signal Exit",
                marker=dict(symbol="circle", size=10, color="#f39c12"),
            ))

        if end_exits:
            fig.add_trace(go.Scatter(
                x=[e[0] for e in end_exits],
                y=[e[1] for e in end_exits],
                mode="markers",
                name="End of Data Exit",
                marker=dict(symbol="diamond", size=10, color="#95a5a6"),
            ))

        # Draw SL and TP lines for each trade
        for t in trades:
            # SL line
            fig.add_trace(go.Scatter(
                x=[t.entry_date, t.exit_date],
                y=[t.sl_price, t.sl_price],
                mode="lines",
                name=f"SL {t.direction}",
                line=dict(color="#e74c3c", width=1, dash="dash"),
                showlegend=False,
                hovertemplate=f"SL: {t.sl_price:.0f}<br>{t.entry_date} to {t.exit_date}",
            ))
            # TP1 line
            if t.tp1_price is not None:
                fig.add_trace(go.Scatter(
                    x=[t.entry_date, t.exit_date],
                    y=[t.tp1_price, t.tp1_price],
                    mode="lines",
                    name="TP1",
                    line=dict(color="#27ae60", width=1, dash="dot"),
                    showlegend=False,
                    hovertemplate=f"TP1: {t.tp1_price:.0f}",
                ))

    fig.update_layout(
        title="Price Chart with Trade Markers",
        xaxis_title="Date",
        yaxis_title="Price (Rp)",
        hovermode="x unified",
        template="plotly_white",
        height=500,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )

    return fig


def plot_drawdown(equity_curve: List[Tuple]) -> "plotly.graph_objects.Figure":
    """
    Plot drawdown from peak equity.
    """
    import plotly.graph_objects as go

    if not equity_curve:
        fig = go.Figure()
        fig.update_layout(title="No equity data available")
        return fig

    dates = [e[0] for e in equity_curve]
    values = [e[1] for e in equity_curve]

    # Calculate drawdown
    peak = values[0]
    drawdowns = []
    for v in values:
        if v > peak:
            peak = v
        dd = (peak - v) / peak * 100.0 if peak > 0 else 0.0
        drawdowns.append(dd)

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=dates,
        y=drawdowns,
        mode="lines",
        name="Drawdown %",
        line=dict(color="#e74c3c", width=2),
        fill="tozeroy",
        fillcolor="rgba(231,76,60,0.15)",
    ))

    fig.update_layout(
        title="Drawdown from Peak",
        xaxis_title="Date",
        yaxis_title="Drawdown (%)",
        hovermode="x unified",
        template="plotly_white",
        height=300,
    )

    return fig


def plot_r_multiples(trades: List[Trade]) -> "plotly.graph_objects.Figure":
    """
    Plot R-multiples bar chart for each trade.
    """
    import plotly.graph_objects as go

    if not trades:
        fig = go.Figure()
        fig.update_layout(title="No trades to display")
        return fig

    labels = [f"{t.entry_date.strftime('%m/%d')} → {t.exit_date.strftime('%m/%d')}" for t in trades]
    r_values = [t.r_multiple for t in trades]
    colors = ["#27ae60" if r > 0 else "#e74c3c" for r in r_values]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=labels,
        y=r_values,
        marker_color=colors,
        name="R-multiple",
    ))

    fig.update_layout(
        title="R-Multiples per Trade",
        xaxis_title="Trade",
        yaxis_title="R-multiple",
        template="plotly_white",
        height=300,
    )

    return fig


def render_backtest_charts(result: BacktestResult, df: pd.DataFrame):
    """
    Render all backtest charts. Returns a list of plotly figures.
    """
    charts = []

    # Equity curve
    if result.equity_curve:
        charts.append(("equity", plot_equity_curve(result.equity_curve)))

    # Price with trades
    charts.append(("price_trades", plot_price_with_trades(df, result.trades)))

    # Drawdown
    if result.equity_curve:
        charts.append(("drawdown", plot_drawdown(result.equity_curve)))

    # R-multiples
    if result.trades:
        charts.append(("r_multiples", plot_r_multiples(result.trades)))

    return charts
