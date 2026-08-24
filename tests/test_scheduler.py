"""Tests for scheduler module."""

import pytest
import pandas as pd
import json
import os
import tempfile

from bei_swing_engine_v8.scheduler import (
    SchedulerConfig, SignalAlert, format_alerts_text,
    save_alerts_json, load_config_from_file, save_config_to_file,
    run_scheduler, run_optimization_cycle,
)


class TestScheduler:
    def test_scheduler_config_defaults(self):
        config = SchedulerConfig()
        assert len(config.tickers) == 3
        assert config.ihsg is True
        assert config.period == "1y"
        assert config.email_enabled is False
        assert "BUY" in config.notify_on

    def test_signal_alert_dataclass(self):
        alert = SignalAlert(
            ticker="TLKM", decision="BUY", direction="LONG",
            thesis="BULLISH", setup="Pullback TRIGGERED",
            entry=2610, sl=2600, tp1=2780, rr=17.0, close=2610,
            timestamp="2026-08-25 10:00:00",
        )
        assert alert.ticker == "TLKM"
        assert alert.decision == "BUY"

    def test_format_alerts_empty(self):
        text = format_alerts_text([])
        assert "No actionable signals" in text

    def test_format_alerts_with_signals(self):
        alerts = [
            SignalAlert(
                ticker="TLKM", decision="BUY", direction="LONG",
                thesis="BULLISH", setup="Pullback TRIGGERED",
                entry=2610, sl=2600, tp1=2780, rr=17.0, close=2610,
                timestamp="2026-08-25 10:00:00",
            ),
        ]
        text = format_alerts_text(alerts)
        assert "TLKM" in text
        assert "BUY" in text
        assert "Disclaimer" in text

    def test_save_alerts_json(self):
        alerts = [
            SignalAlert(
                ticker="TLKM", decision="BUY", direction="LONG",
                thesis="BULLISH", setup="Pullback TRIGGERED",
                entry=2610, sl=2600, tp1=2780, rr=17.0, close=2610,
                timestamp="2026-08-25 10:00:00",
            ),
        ]
        temp_dir = tempfile.mkdtemp()
        path = save_alerts_json(alerts, temp_dir)
        assert os.path.exists(path)
        with open(path, "r") as f:
            data = json.load(f)
        assert len(data) == 1
        assert data[0]["ticker"] == "TLKM"

    def test_save_alerts_json_empty(self):
        temp_dir = tempfile.mkdtemp()
        path = save_alerts_json([], temp_dir)
        assert os.path.exists(path)
        with open(path, "r") as f:
            data = json.load(f)
        assert data == []

    def test_save_and_load_config(self):
        config = SchedulerConfig(
            tickers=["BBRI", "TLKM"],
            period="2y",
            email_enabled=True,
            email_smtp_host="smtp.gmail.com",
            email_to=["test@email.com"],
        )
        temp_dir = tempfile.mkdtemp()
        path = os.path.join(temp_dir, "test_config.json")
        save_config_to_file(config, path)
        assert os.path.exists(path)

        loaded = load_config_from_file(path)
        assert loaded.tickers == ["BBRI", "TLKM"]
        assert loaded.period == "2y"
        assert loaded.email_enabled is True
        assert loaded.email_smtp_host == "smtp.gmail.com"

    def test_load_config_nonexistent_file(self):
        with pytest.raises(FileNotFoundError):
            load_config_from_file("nonexistent_config.json")

    def test_scheduler_config_optimization_defaults(self):
        config = SchedulerConfig()
        assert config.optimize_enabled is False
        assert config.optimize_interval_days == 7
        assert config.optimize_step == 5
        assert config.optimize_windows == 2
        assert config.optimize_last_run == ""

    def test_scheduler_config_optimization_custom(self):
        config = SchedulerConfig(
            optimize_enabled=True,
            optimize_interval_days=14,
            optimize_step=1,
            optimize_windows=3,
        )
        assert config.optimize_enabled is True
        assert config.optimize_interval_days == 14
        assert config.optimize_step == 1
        assert config.optimize_windows == 3

    def test_save_load_config_with_optimization(self):
        config = SchedulerConfig(
            tickers=["BBRI"],
            optimize_enabled=True,
            optimize_interval_days=14,
            optimize_step=1,
            optimize_windows=3,
            optimize_last_run="2026-08-20",
        )
        temp_dir = tempfile.mkdtemp()
        path = os.path.join(temp_dir, "opt_config.json")
        save_config_to_file(config, path)
        loaded = load_config_from_file(path)
        assert loaded.optimize_enabled is True
        assert loaded.optimize_interval_days == 14
        assert loaded.optimize_step == 1
        assert loaded.optimize_windows == 3
        assert loaded.optimize_last_run == "2026-08-20"

    def test_run_optimization_cycle_disabled(self):
        config = SchedulerConfig(optimize_enabled=False)
        result = run_optimization_cycle(config)
        assert result is None
