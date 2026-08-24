"""Tests for merger module — extended coverage."""

import pytest
import os
import tempfile

from bei_swing_engine_v8.merger import (
    merge_csv, merge_csv_files, parse_cleaned_csv, MergeResult,
)
from bei_swing_engine_v8.cleaner import rows_to_csv_string


class TestMergerExtended:
    def test_merge_csv_error_no_existing(self):
        result = merge_csv("invalid,csv,format", [("new.csv", "Date,Open,High,Low,Close,Volume\n2026-01-01,100,102,99,101,1000\n")])
        assert result.error is not None

    def test_merge_csv_with_output_name(self):
        existing = "Date,Open,High,Low,Close,Volume\n2026-01-01,100,102,99,101,1000\n"
        new = "Date,Open,High,Low,Close,Volume\n2026-01-02,101,103,100,102,2000\n"
        result = merge_csv(existing, [("new.csv", new)], output_name="custom.csv")
        assert result.output_name == "custom.csv"

    def test_merge_csv_new_file_error(self):
        existing = "Date,Open,High,Low,Close,Volume\n2026-01-01,100,102,99,101,1000\n"
        new = "bad,csv\n"
        result = merge_csv(existing, [("bad.csv", new)])
        # Should still succeed, just with 0 new rows
        assert result.error is None or result.new_count == 0

    def test_merge_csv_files(self):
        temp_dir = tempfile.mkdtemp()

        existing_path = os.path.join(temp_dir, "existing.csv")
        with open(existing_path, "w") as f:
            f.write("Date,Open,High,Low,Close,Volume\n2026-01-01,100,102,99,101,1000\n")

        new_path = os.path.join(temp_dir, "new.csv")
        with open(new_path, "w") as f:
            f.write("Date,Open,High,Low,Close,Volume\n2026-01-02,101,103,100,102,2000\n")

        result = merge_csv_files(existing_path, [new_path], temp_dir)
        assert result.error is None
        assert result.new_count == 1
        assert result.merged_count == 2
        # Check output file exists
        assert os.path.exists(os.path.join(temp_dir, result.output_name))

    def test_merge_csv_files_nonexistent(self):
        # merge_csv_files should raise FileNotFoundError for nonexistent existing file
        with pytest.raises(FileNotFoundError):
            merge_csv_files("nonexistent.csv", ["also_nonexistent.csv"], ".")

    def test_parse_cleaned_csv_empty(self):
        rows, dates = parse_cleaned_csv("")
        assert rows == []
        assert dates == set()

    def test_parse_cleaned_csv_alias_mapping(self):
        text = "tanggal,buka,tertinggi,terendah,penutupan,jumlah\n2026-01-01,100,102,99,101,1000\n"
        rows, dates = parse_cleaned_csv(text)
        assert len(rows) == 1
        assert "2026-01-01" in dates

    def test_merge_result_dataclass(self):
        r = MergeResult(
            existing_count=10, new_count=5, merged_count=15,
            first_date="2026-01-01", last_date="2026-02-01",
            new_dates=["2026-01-15"], rows=[],
            output_name="merged.csv",
        )
        assert r.merged_count == 15
        assert len(r.new_dates) == 1
