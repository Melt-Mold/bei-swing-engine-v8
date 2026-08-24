"""Tests for cleaner module — extended coverage."""

import pytest
import os
import tempfile

from bei_swing_engine_v8.cleaner import (
    clean_csv_text, clean_csv_file, write_cleaned_csv, rows_to_csv_string,
    _parse_date, _clean_number, _find_columns, _detect_source, CleanResult,
)


class TestCleanerExtended:
    def test_clean_number_european_format(self):
        # European: "1.234,56" → after removing commas and keeping last dot
        result = _clean_number("1.234.567")
        assert "." in result  # Should keep last dot as decimal

    def test_clean_number_empty(self):
        assert _clean_number("") == ""
        assert _clean_number(None) == ""

    def test_parse_date_iso_with_time(self):
        date, fmt = _parse_date("2026-08-21T00:00:00")
        assert date == "2026-08-21"
        assert fmt == "ISO 8601"

    def test_parse_date_unix_seconds(self):
        # 2026-08-21 in Unix timestamp
        import datetime
        d = datetime.datetime(2026, 8, 21)
        ts = int(d.timestamp())
        date, fmt = _parse_date(str(ts))
        assert date is not None
        assert "Unix" in fmt

    def test_parse_date_unix_ms(self):
        import datetime
        d = datetime.datetime(2026, 8, 21)
        ts = int(d.timestamp() * 1000)
        date, fmt = _parse_date(str(ts))
        assert date is not None
        assert "Unix" in fmt

    def test_parse_date_dd_mm_yyyy(self):
        date, fmt = _parse_date("21/08/2026")
        assert date == "2026-08-21"

    def test_parse_date_mm_dd_yyyy(self):
        date, fmt = _parse_date("08/21/2026")
        assert date == "2026-08-21"

    def test_parse_date_dd_dot_mm_dot_yyyy(self):
        date, fmt = _parse_date("21.08.2026")
        assert date == "2026-08-21"

    def test_parse_date_unknown(self):
        date, fmt = _parse_date("not-a-date")
        assert date is None
        assert fmt == "Unknown"

    def test_find_columns_standard(self):
        header = ["date", "open", "high", "low", "close", "volume"]
        col_map = _find_columns(header)
        assert col_map["date"] == 0
        assert col_map["open"] == 1
        assert col_map["close"] == 4

    def test_find_columns_indonesian(self):
        header = ["tanggal", "buka", "tertinggi", "terendah", "penutupan", "jumlah"]
        col_map = _find_columns(header)
        assert col_map["date"] == 0
        assert col_map["open"] == 1
        assert col_map["close"] == 4

    def test_find_columns_adj_close(self):
        header = ["date", "open", "high", "low", "adj close", "volume"]
        col_map = _find_columns(header)
        assert col_map["close"] == 4  # adj close maps to close

    def test_detect_source_yahoo(self):
        header = ["date", "open", "high", "low", "close", "adj close", "volume"]
        source = _detect_source(header)
        assert source == "Yahoo Finance"

    def test_detect_source_investing(self):
        header = ["date", "price", "open", "high", "low", "change %", "vol"]
        source = _detect_source(header)
        assert source == "Investing.com"

    def test_detect_source_unknown(self):
        header = ["date", "open", "high", "low", "close", "volume"]
        source = _detect_source(header)
        assert source == "Unknown"

    def test_write_cleaned_csv(self):
        rows = [
            {"date": "2026-01-01", "open": 100, "high": 102, "low": 99, "close": 101, "volume": 1000},
            {"date": "2026-01-02", "open": 101, "high": 103, "low": 100, "close": 102, "volume": 2000},
        ]
        temp_dir = tempfile.mkdtemp()
        path = os.path.join(temp_dir, "test.csv")
        write_cleaned_csv(rows, path)
        assert os.path.exists(path)
        with open(path, "r") as f:
            content = f.read()
        assert "Date,Open,High,Low,Close,Volume" in content
        assert "2026-01-01" in content

    def test_rows_to_csv_string(self):
        rows = [
            {"date": "2026-01-01", "open": 100, "high": 102, "low": 99, "close": 101, "volume": 1000},
        ]
        csv_str = rows_to_csv_string(rows)
        assert "Date,Open,High,Low,Close,Volume" in csv_str
        assert "2026-01-01" in csv_str

    def test_clean_csv_file(self):
        # Create a test CSV
        temp_dir = tempfile.mkdtemp()
        input_path = os.path.join(temp_dir, "test.csv")
        with open(input_path, "w") as f:
            f.write("Date,Open,High,Low,Close,Volume\n2026-01-02,101,103,100,102,2000\n2026-01-01,100,102,99,101,1000\n")

        result = clean_csv_file(input_path, temp_dir)
        assert result.error is None
        assert result.row_count == 2
        # Should be sorted
        assert result.rows[0]["date"] == "2026-01-01"
        assert result.rows[1]["date"] == "2026-01-02"
        assert os.path.exists(os.path.join(temp_dir, result.output_name))

    def test_clean_csv_empty_text(self):
        result = clean_csv_text("", "empty.csv")
        assert result.error is not None

    def test_clean_csv_not_enough_rows(self):
        result = clean_csv_text("Date,Open\n", "bad.csv")
        assert result.error is not None

    def test_clean_result_dataclass(self):
        r = CleanResult(rows=[], row_count=0, delimiter=",",
                        date_format="Unknown", source="Unknown",
                        output_name="test.csv", error="test error")
        assert r.error == "test error"
        assert r.row_count == 0
