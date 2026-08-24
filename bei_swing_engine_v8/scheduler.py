"""
Scheduler automation module.
Auto-fetches data from Yahoo Finance, runs analysis, and notifies on BUY/SELL signals.
Can run once or on a recurring schedule.
"""

import os
import time
import json
import smtplib
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from dataclasses import dataclass, field

from .logging_config import get_logger

_log = get_logger("scheduler")


@dataclass
class SchedulerConfig:
    """Configuration for the scheduler."""
    tickers: List[str] = field(default_factory=lambda: ["BBRI", "BBCA", "TLKM"])
    ihsg: bool = True
    period: str = "1y"
    interval: str = "1d"
    params: Dict = field(default_factory=lambda: {
        "MODE": "C",
        "HORIZON": "SWING",
        "DIRECTION": "BOTH",
        "POSITION": "NO_POSITION",
        "MODAL": 10000000,
        "RISK": 2.0,
        "OUTPUT": "Chat",
        "IHSG": "uploaded",
    })
    output_dir: str = "output"
    data_dir: str = "data-scheduled"
    # Email notification (optional)
    email_enabled: bool = False
    email_smtp_host: str = ""
    email_smtp_port: int = 587
    email_user: str = ""
    email_password: str = ""
    email_to: List[str] = field(default_factory=list)
    # Schedule
    run_once: bool = False
    interval_minutes: int = 0  # 0 = run once; >0 = recurring
    # Signal filter: only notify on these decisions
    notify_on: List[str] = field(default_factory=lambda: ["BUY", "SELL"])
    # Optimization settings (auto-optimize parameters periodically)
    optimize_enabled: bool = False
    optimize_interval_days: int = 7  # Run optimization every N days
    optimize_step: int = 5  # Backtest step for optimization
    optimize_windows: int = 2  # Walk-forward windows
    optimize_last_run: str = ""  # ISO date of last optimization run


@dataclass
class SignalAlert:
    """A signal alert for notification."""
    ticker: str
    decision: str
    direction: str
    thesis: str
    setup: str
    entry: Optional[float]
    sl: Optional[float]
    tp1: Optional[float]
    rr: Optional[float]
    close: float
    timestamp: str


def fetch_and_analyze(config: SchedulerConfig) -> List[SignalAlert]:
    """
    Fetch data for all tickers, run analysis, and return signal alerts.
    """
    from .fetcher import fetch_and_save
    from .data import load_ohlcv, load_ihsg
    from .engine import analyze_ticker
    from .structure import analyze_structure

    os.makedirs(config.data_dir, exist_ok=True)
    alerts = []

    # Fetch IHSG if enabled
    ihsg_path = None
    if config.ihsg:
        _log.info("fetching IHSG...")
        result = fetch_and_save("IHSG", period=config.period, interval=config.interval, output_dir=config.data_dir)
        if not result.error:
            ihsg_path = os.path.join(config.data_dir, "IHSG-JKSE_cleaned.csv")
        else:
            _log.warning("IHSG fetch failed: %s", result.error)

    # Fetch and analyze each ticker
    for ticker in config.tickers:
        _log.info("processing ticker=%s", ticker)
        result = fetch_and_save(ticker, period=config.period, interval=config.interval, output_dir=config.data_dir)
        if result.error:
            _log.error("fetch failed | ticker=%s error=%s", ticker, result.error)
            continue

        path = os.path.join(config.data_dir, result.output_name)
        if not os.path.exists(path):
            _log.error("file not found | ticker=%s path=%s", ticker, path)
            continue

        try:
            df = load_ohlcv(path)
            ihsg_df = load_ihsg(ihsg_path) if ihsg_path else None
            analysis = analyze_ticker(df, config.params, ihsg_df)

            if analysis.get("status") != "OK":
                _log.warning("analysis failed | ticker=%s status=%s", ticker, analysis.get("status"))
                continue

            dec = analysis["decision"]
            setup = analysis["primary_setup"]

            alert = SignalAlert(
                ticker=ticker,
                decision=dec.decision,
                direction=dec.decision_direction,
                thesis=dec.thesis_state,
                setup=f"{setup.type} {setup.direction} {setup.status}",
                entry=dec.entry,
                sl=dec.sl,
                tp1=dec.tp1,
                rr=dec.rr_raw,
                close=df["Close"].iloc[-1],
                timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            )

            # Log all decisions
            _log.info("signal | ticker=%s decision=%s direction=%s thesis=%s setup=%s entry=%s sl=%s tp1=%s rr=%s",
                      alert.ticker, alert.decision, alert.direction, alert.thesis,
                      alert.setup, alert.entry, alert.sl, alert.tp1, alert.rr)

            # Only collect alerts for configured decisions
            if alert.decision in config.notify_on:
                alerts.append(alert)

        except Exception as e:
            _log.error("analysis error | ticker=%s error=%s", ticker, e)

    return alerts


def format_alerts_text(alerts: List[SignalAlert]) -> str:
    """Format alerts as readable text for console/email."""
    if not alerts:
        return "No actionable signals today. All tickers are WAIT/NO_SETUP."

    lines = ["=== BEI Swing Engine v8.0 — Signal Alerts ===", ""]
    lines.append(f"Date: {alerts[0].timestamp}")
    lines.append(f"Actionable signals: {len(alerts)}")
    lines.append("")

    for a in alerts:
        lines.append(f"[{a.decision}] {a.ticker} ({a.direction})")
        lines.append(f"  Thesis: {a.thesis}")
        lines.append(f"  Setup: {a.setup}")
        lines.append(f"  Close: {a.close:.0f}")
        if a.entry:
            lines.append(f"  Entry: {a.entry:.0f} | SL: {a.sl:.0f} | TP1: {a.tp1:.0f} | R/R: {a.rr:.2f}")
        lines.append("")

    lines.append("---")
    lines.append("Disclaimer: Analisa ini bersifat edukatif, BUKAN rekomendasi investasi.")
    return "\n".join(lines)


def save_alerts_json(alerts: List[SignalAlert], output_dir: str) -> str:
    """Save alerts to JSON file. Returns the file path."""
    os.makedirs(output_dir, exist_ok=True)
    date_str = datetime.now().strftime("%Y-%m-%d")
    path = os.path.join(output_dir, f"signals_{date_str}.json")

    data = []
    for a in alerts:
        data.append({
            "ticker": a.ticker,
            "decision": a.decision,
            "direction": a.direction,
            "thesis": a.thesis,
            "setup": a.setup,
            "entry": a.entry,
            "sl": a.sl,
            "tp1": a.tp1,
            "rr": a.rr,
            "close": a.close,
            "timestamp": a.timestamp,
        })

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    _log.info("alerts saved | path=%s count=%d", path, len(alerts))
    return path


def send_email_notification(config: SchedulerConfig, subject: str, body: str) -> bool:
    """Send email notification. Returns True on success."""
    if not config.email_enabled or not config.email_smtp_host:
        return False

    try:
        import email.message
        msg = email.message.EmailMessage()
        msg["Subject"] = subject
        msg["From"] = config.email_user
        msg["To"] = ", ".join(config.email_to)
        msg.set_content(body)

        with smtplib.SMTP(config.email_smtp_host, config.email_smtp_port) as server:
            server.starttls()
            server.login(config.email_user, config.email_password)
            server.send_message(msg)

        _log.info("email sent | to=%s subject=%s", config.email_to, subject)
        return True
    except Exception as e:
        _log.error("email failed | error=%s", e)
        return False


def run_optimization_cycle(config: SchedulerConfig) -> Optional[str]:
    """
    Run optimization for all tickers and save reports.
    Returns the combined optimization report text (or None if disabled).
    """
    if not config.optimize_enabled:
        return None

    from .optimizer import run_optimization, render_optimization_report, save_optimization_report

    _log.info("optimization cycle start | tickers=%s", config.tickers)

    os.makedirs(config.data_dir, exist_ok=True)
    os.makedirs(config.output_dir, exist_ok=True)

    all_reports = []
    base_params = {**config.params, "IHSG": "None", "MODE": "A"}

    for ticker in config.tickers:
        _log.info("optimizing | ticker=%s", ticker)

        # Try to load existing fetched data
        clean_ticker = ticker.upper().replace("^", "").replace(".JK", "")
        path = os.path.join(config.data_dir, f"{clean_ticker}.JK_cleaned.csv")

        if not os.path.exists(path):
            # Fetch if not available
            from .fetcher import fetch_and_save
            result = fetch_and_save(ticker, period=config.period, interval=config.interval, output_dir=config.data_dir)
            if result.error:
                _log.error("fetch failed for optimization | ticker=%s error=%s", ticker, result.error)
                continue
            path = os.path.join(config.data_dir, result.output_name)

        try:
            from .data import load_ohlcv
            df = load_ohlcv(path)

            report = run_optimization(
                df=df,
                base_params=base_params,
                step=config.optimize_step,
                n_windows=config.optimize_windows,
            )

            report_text = render_optimization_report(report)
            save_optimization_report(report, config.output_dir)
            all_reports.append(report_text)

            _log.info("optimization done | ticker=%s best_score=%.3f",
                      ticker, report.best_result.score)

        except Exception as e:
            _log.error("optimization failed | ticker=%s error=%s", ticker, e)

    # Update last run date
    config.optimize_last_run = datetime.now().strftime("%Y-%m-%d")

    combined = "\n\n---\n\n".join(all_reports) if all_reports else "No optimization results."

    # Email notification
    if config.email_enabled and all_reports:
        send_email_notification(
            config,
            subject=f"BEI Swing Engine — Optimization Report — {config.optimize_last_run}",
            body=combined,
        )

    _log.info("optimization cycle done | reports=%d", len(all_reports))
    return combined


def run_scheduler(config: SchedulerConfig) -> List[SignalAlert]:
    """
    Run the scheduler: fetch data, analyze, notify.
    If config.interval_minutes > 0, runs in a loop.
    Also runs optimization periodically if enabled.
    """
    _log.info("scheduler started | tickers=%s ihsg=%s period=%s",
              config.tickers, config.ihsg, config.period)

    # Check if optimization should run
    if config.optimize_enabled:
        should_optimize = True
        if config.optimize_last_run:
            try:
                last_date = datetime.strptime(config.optimize_last_run, "%Y-%m-%d")
                days_since = (datetime.now() - last_date).days
                if days_since < config.optimize_interval_days:
                    should_optimize = False
                    _log.info("optimization skipped | last_run=%s days_since=%d interval=%d",
                              config.optimize_last_run, days_since, config.optimize_interval_days)
            except ValueError:
                pass  # Invalid date format, run optimization

        if should_optimize:
            _log.info("running optimization cycle...")
            run_optimization_cycle(config)

    alerts = fetch_and_analyze(config)

    # Format and log alerts
    text = format_alerts_text(alerts)
    print(text)

    # Save to JSON
    save_alerts_json(alerts, config.output_dir)

    # Save to markdown report
    date_str = datetime.now().strftime("%Y-%m-%d")
    md_path = os.path.join(config.output_dir, f"signals_{date_str}.md")
    os.makedirs(config.output_dir, exist_ok=True)
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(text)
    _log.info("report saved | path=%s", md_path)

    # Email notification
    if config.email_enabled and alerts:
        send_email_notification(
            config,
            subject=f"BEI Swing Engine — {len(alerts)} Signal(s) — {date_str}",
            body=text,
        )

    _log.info("scheduler done | alerts=%d", len(alerts))
    return alerts


def run_scheduler_loop(config: SchedulerConfig):
    """
    Run scheduler in a loop with specified interval.
    Press Ctrl+C to stop.
    """
    if config.interval_minutes <= 0:
        run_scheduler(config)
        return

    _log.info("scheduler loop | interval=%d minutes", config.interval_minutes)

    try:
        while True:
            run_scheduler(config)
            _log.info("sleeping %d minutes...", config.interval_minutes)
            time.sleep(config.interval_minutes * 60)
    except KeyboardInterrupt:
        _log.info("scheduler stopped by user")


def load_config_from_file(path: str) -> SchedulerConfig:
    """Load scheduler config from JSON file."""
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    return SchedulerConfig(
        tickers=data.get("tickers", ["BBRI", "BBCA", "TLKM"]),
        ihsg=data.get("ihsg", True),
        period=data.get("period", "1y"),
        interval=data.get("interval", "1d"),
        params=data.get("params", {
            "MODE": "C", "HORIZON": "SWING", "DIRECTION": "BOTH",
            "POSITION": "NO_POSITION", "MODAL": 10000000, "RISK": 2.0,
            "OUTPUT": "Chat", "IHSG": "uploaded",
        }),
        output_dir=data.get("output_dir", "output"),
        data_dir=data.get("data_dir", "data-scheduled"),
        email_enabled=data.get("email_enabled", False),
        email_smtp_host=data.get("email_smtp_host", ""),
        email_smtp_port=data.get("email_smtp_port", 587),
        email_user=data.get("email_user", ""),
        email_password=data.get("email_password", ""),
        email_to=data.get("email_to", []),
        run_once=data.get("run_once", False),
        interval_minutes=data.get("interval_minutes", 0),
        notify_on=data.get("notify_on", ["BUY", "SELL"]),
        optimize_enabled=data.get("optimize_enabled", False),
        optimize_interval_days=data.get("optimize_interval_days", 7),
        optimize_step=data.get("optimize_step", 5),
        optimize_windows=data.get("optimize_windows", 2),
        optimize_last_run=data.get("optimize_last_run", ""),
    )


def save_config_to_file(config: SchedulerConfig, path: str):
    """Save scheduler config to JSON file."""
    data = {
        "tickers": config.tickers,
        "ihsg": config.ihsg,
        "period": config.period,
        "interval": config.interval,
        "params": config.params,
        "output_dir": config.output_dir,
        "data_dir": config.data_dir,
        "email_enabled": config.email_enabled,
        "email_smtp_host": config.email_smtp_host,
        "email_smtp_port": config.email_smtp_port,
        "email_user": config.email_user,
        "email_password": config.email_password,
        "email_to": config.email_to,
        "run_once": config.run_once,
        "interval_minutes": config.interval_minutes,
        "notify_on": config.notify_on,
        "optimize_enabled": config.optimize_enabled,
        "optimize_interval_days": config.optimize_interval_days,
        "optimize_step": config.optimize_step,
        "optimize_windows": config.optimize_windows,
        "optimize_last_run": config.optimize_last_run,
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
