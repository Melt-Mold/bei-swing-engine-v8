"""Tests for CSV cleaner module."""

import pytest

from bei_swing_engine_v8.cleaner import clean_csv_text, _parse_date, _clean_number


class TestCleaner:
    def test_clean_yahoo_format(self):
        csv = "Date,Open,High,Low,Close,Adj Close,Volume\n2026-01-01,100,102,99,101,100,1000\n2026-01-02,101,103,100,102,101,2000\n"
        result = clean_csv_text(csv, "test.csv")
        assert result.error is None
        assert result.row_count == 2
        assert result.rows[0]["date"] == "2026-01-01"
        assert result.rows[0]["open"] == 100

    def test_clean_semicolon_delimiter(self):
        csv = "Date;Open;High;Low;Close;Volume\n2026-01-01;100;102;99;101;1000\n"
        result = clean_csv_text(csv, "test.csv")
        assert result.error is None
        assert result.row_count == 1
        assert result.delimiter == ";"

    def test_clean_yahoo_date_format(self):
        # Use d MMM yyyy format (no comma in date field)
        csv = "Date,Open,High,Low,Close,Volume\n21 Aug 2026,100,102,99,101,1000\n"
        result = clean_csv_text(csv, "test.csv")
        assert result.error is None
        assert result.row_count == 1
        assert result.rows[0]["date"] == "2026-08-21"
        assert result.date_format == "d MMM yyyy"

    def test_clean_sort_ascending(self):
        csv = "Date,Open,High,Low,Close,Volume\n2026-01-03,103,104,100,102,3000\n2026-01-01,100,102,99,101,1000\n2026-01-02,101,103,100,102,2000\n"
        result = clean_csv_text(csv, "test.csv")
        assert result.rows[0]["date"] == "2026-01-01"
        assert result.rows[1]["date"] == "2026-01-02"
        assert result.rows[2]["date"] == "2026-01-03"

    def test_clean_remove_duplicates(self):
        csv = "Date,Open,High,Low,Close,Volume\n2026-01-01,100,102,99,101,1000\n2026-01-01,100,102,99,101,1000\n"
        result = clean_csv_text(csv, "test.csv")
        assert result.row_count == 1

    def test_clean_validate_low_high(self):
        csv = "Date,Open,High,Low,Close,Volume\n2026-01-01,100,99,102,101,1000\n"
        result = clean_csv_text(csv, "test.csv")
        # low > high should be skipped
        assert result.row_count == 0

    def test_clean_missing_columns(self):
        csv = "Date,Open,Close\n2026-01-01,100,101\n"
        result = clean_csv_text(csv, "test.csv")
        assert result.error is not None
        assert "High" in result.error

    def test_parse_date_formats(self):
        date, fmt = _parse_date("2026-08-21")
        assert date == "2026-08-21" and fmt == "YYYY-MM-DD"

        date, fmt = _parse_date("Aug 21, 2026")
        assert date == "2026-08-21" and fmt == "MMM d, yyyy"

        date, fmt = _parse_date("21 Aug 2026")
        assert date == "2026-08-21" and fmt == "d MMM yyyy"

        date, fmt = _parse_date("21/08/2026")
        assert date == "2026-08-21"

        date, fmt = _parse_date("20260821")
        assert date == "2026-08-21" and fmt == "YYYYMMDD"

    def test_clean_number(self):
        assert _clean_number('"1,000.50"') == "1000.50"
        assert _clean_number("Rp 1.500") == "1.500"
        # Multiple dots: keeps only last as decimal separator
        assert _clean_number("1.234.567") == "1234.567"
