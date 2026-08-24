"""Tests for CSV merger module."""

import pytest

from bei_swing_engine_v8.merger import merge_csv, parse_cleaned_csv


class TestMerger:
    def test_merge_new_data(self):
        existing = "Date,Open,High,Low,Close,Volume\n2026-01-01,100,102,99,101,1000\n2026-01-02,101,103,100,102,2000\n"
        new = "Date,Open,High,Low,Close,Volume\n2026-01-03,103,104,100,102,3000\n2026-01-04,102,105,101,103,4000\n"
        result = merge_csv(existing, [("new.csv", new)])
        assert result.error is None
        assert result.existing_count == 2
        assert result.new_count == 2
        assert result.merged_count == 4
        assert result.new_dates == ["2026-01-03", "2026-01-04"]

    def test_merge_no_new_data(self):
        existing = "Date,Open,High,Low,Close,Volume\n2026-01-01,100,102,99,101,1000\n"
        new = "Date,Open,High,Low,Close,Volume\n2026-01-01,100,102,99,101,1000\n"
        result = merge_csv(existing, [("new.csv", new)])
        assert result.error is None
        assert result.new_count == 0
        assert result.merged_count == 1

    def test_merge_partial_new(self):
        existing = "Date,Open,High,Low,Close,Volume\n2026-01-01,100,102,99,101,1000\n2026-01-02,101,103,100,102,2000\n"
        new = "Date,Open,High,Low,Close,Volume\n2026-01-02,101,103,100,102,2000\n2026-01-03,103,104,100,102,3000\n"
        result = merge_csv(existing, [("new.csv", new)])
        assert result.new_count == 1
        assert result.merged_count == 3
        assert result.new_dates == ["2026-01-03"]

    def test_parse_cleaned_csv(self):
        text = "Date,Open,High,Low,Close,Volume\n2026-01-01,100,102,99,101,1000\n"
        rows, dates = parse_cleaned_csv(text)
        assert len(rows) == 1
        assert "2026-01-01" in dates
        assert rows[0]["close"] == 101

    def test_merge_multiple_new_files(self):
        existing = "Date,Open,High,Low,Close,Volume\n2026-01-01,100,102,99,101,1000\n"
        new1 = "Date,Open,High,Low,Close,Volume\n2026-01-02,101,103,100,102,2000\n"
        new2 = "Date,Open,High,Low,Close,Volume\n2026-01-03,103,104,100,102,3000\n"
        result = merge_csv(existing, [("n1.csv", new1), ("n2.csv", new2)])
        assert result.new_count == 2
        assert result.merged_count == 3
