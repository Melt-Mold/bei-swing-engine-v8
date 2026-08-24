"""
CSV Merger — Python port of SwingFlow v7.0 CSV Merger.
Appends new data from raw Yahoo Finance CSV to an existing cleaned CSV file.
Only adds dates that don't already exist in the existing file.
"""

import os
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

from .cleaner import clean_csv_text, write_cleaned_csv, rows_to_csv_string, _parse_date, _clean_number, _find_columns
from .logging_config import get_logger

_log = get_logger("merger")


@dataclass
class MergeResult:
    """Result of merging new data into existing."""
    existing_count: int
    new_count: int
    merged_count: int
    first_date: str
    last_date: str
    new_dates: List[str]
    rows: List[Dict]
    output_name: str
    error: Optional[str] = None


def parse_cleaned_csv(text: str) -> Tuple[List[Dict], set]:
    """
    Parse an already-cleaned CSV (or raw CSV via alias mapping).
    Returns (rows, set_of_dates).
    """
    text = text.lstrip("\ufeff")
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    lines = [l for l in lines if l.strip()]
    if len(lines) < 2:
        return [], set()

    header = [h.replace('"', '').strip().lower() for h in lines[0].split(",")]

    # Try standard format first
    date_idx = header.index("date") if "date" in header else -1
    open_idx = header.index("open") if "open" in header else -1
    high_idx = header.index("high") if "high" in header else -1
    low_idx = header.index("low") if "low" in header else -1
    close_idx = header.index("close") if "close" in header else -1
    vol_idx = header.index("volume") if "volume" in header else -1

    # If not standard, use alias mapping
    if date_idx == -1 or open_idx == -1:
        col_map = _find_columns(header)
        date_idx = col_map["date"]
        open_idx = col_map["open"]
        high_idx = col_map["high"]
        low_idx = col_map["low"]
        close_idx = col_map["close"]
        vol_idx = col_map["volume"]

    if date_idx == -1 or open_idx == -1 or high_idx == -1 or low_idx == -1 or close_idx == -1:
        return [], set()

    rows = []
    dates = set()

    for line in lines[1:]:
        fields = line.split(",")
        if len(fields) <= max(date_idx, open_idx, high_idx, low_idx, close_idx):
            continue

        date_str = fields[date_idx].replace('"', '').strip()
        date_result, _ = _parse_date(date_str)
        if date_result is None:
            continue

        try:
            open_v = float(_clean_number(fields[open_idx]))
            high_v = float(_clean_number(fields[high_idx]))
            low_v = float(_clean_number(fields[low_idx]))
            close_v = float(_clean_number(fields[close_idx]))
        except (ValueError, IndexError):
            continue

        vol_str = ""
        if vol_idx >= 0 and vol_idx < len(fields):
            vol_str = _clean_number(fields[vol_idx])
        try:
            volume = int(float(vol_str)) if vol_str else 0
        except ValueError:
            volume = 0

        if open_v <= 0 or high_v <= 0 or low_v <= 0 or close_v <= 0:
            continue
        if low_v > high_v:
            continue

        rows.append({"date": date_result, "open": open_v, "high": high_v, "low": low_v, "close": close_v, "volume": volume})
        dates.add(date_result)

    rows.sort(key=lambda r: r["date"])
    return rows, dates


def merge_csv(
    existing_text: str,
    new_texts: List[Tuple[str, str]],  # list of (filename, csv_text)
    output_name: Optional[str] = None,
) -> MergeResult:
    """
    Merge new raw CSV data into existing cleaned CSV.
    Only dates not in existing file are added.

    Args:
        existing_text: Content of existing cleaned CSV.
        new_texts: List of (filename, csv_text) tuples for new raw files.
        output_name: Output filename.

    Returns:
        MergeResult with merged rows.
    """
    # Parse existing
    existing_rows, existing_dates = parse_cleaned_csv(existing_text)
    if not existing_rows:
        return MergeResult(0, 0, 0, "", "", [], [], output_name or "merged.csv",
                          error="Cannot parse existing CSV or no valid rows")

    existing_count = len(existing_rows)
    existing_first = existing_rows[0]["date"]
    existing_last = existing_rows[-1]["date"]

    _log.info("existing loaded | rows=%d range=%s..%s", existing_count, existing_first, existing_last)

    # Clean and collect new rows
    all_new_rows = []
    all_new_dates_set = set()

    for filename, new_text in new_texts:
        result = clean_csv_text(new_text, filename)
        if result.error:
            _log.warning("new file skipped | file=%s error=%s", filename, result.error)
            continue

        new_from_file = []
        for row in result.rows:
            if row["date"] not in existing_dates and row["date"] not in all_new_dates_set:
                new_from_file.append(row)
                all_new_dates_set.add(row["date"])

        if new_from_file:
            all_new_rows.extend(new_from_file)
            _log.info("new data | file=%s new_rows=%d", filename, len(new_from_file))

    if not all_new_rows:
        _log.info("no new data found | all dates already exist")
        return MergeResult(
            existing_count=existing_count,
            new_count=0,
            merged_count=existing_count,
            first_date=existing_first,
            last_date=existing_last,
            new_dates=[],
            rows=existing_rows,
            output_name=output_name or "merged_cleaned.csv",
        )

    # Sort new rows
    all_new_rows.sort(key=lambda r: r["date"])

    # Merge: existing + new, sort, deduplicate
    merged = list(existing_rows)
    merged_dates = set(existing_dates)
    for row in all_new_rows:
        if row["date"] not in merged_dates:
            merged.append(row)
            merged_dates.add(row["date"])
    merged.sort(key=lambda r: r["date"])

    merged_first = merged[0]["date"]
    merged_last = merged[-1]["date"]
    new_dates = [r["date"] for r in all_new_rows]

    _log.info("merge complete | existing=%d new=%d merged=%d range=%s..%s",
              existing_count, len(all_new_rows), len(merged), merged_first, merged_last)

    return MergeResult(
        existing_count=existing_count,
        new_count=len(all_new_rows),
        merged_count=len(merged),
        first_date=merged_first,
        last_date=merged_last,
        new_dates=new_dates,
        rows=merged,
        output_name=output_name or "merged_cleaned.csv",
    )


def merge_csv_files(
    existing_path: str,
    new_paths: List[str],
    output_dir: str = ".",
) -> MergeResult:
    """Merge new CSV files into an existing cleaned CSV file."""
    with open(existing_path, "r", encoding="utf-8-sig") as f:
        existing_text = f.read()

    new_texts = []
    for p in new_paths:
        with open(p, "r", encoding="utf-8-sig") as f:
            new_texts.append((os.path.basename(p), f.read()))

    output_name = os.path.basename(existing_path)
    result = merge_csv(existing_text, new_texts, output_name=output_name)

    if result.error:
        return result

    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, result.output_name)
    write_cleaned_csv(result.rows, output_path)

    return result
