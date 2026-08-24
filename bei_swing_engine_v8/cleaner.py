"""
CSV Cleaner — Python port of SwingFlow v7.0 Universal CSV Cleaner.
Cleans CSV from any source (Yahoo Finance, Investing.com, TradingView, etc.)
into standard format: Date(YYYY-MM-DD),Open,High,Low,Close,Volume
"""

import re
import os
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

from .logging_config import get_logger

_log = get_logger("cleaner")


# Month name → number mapping (EN + ID)
MONTH_MAP = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
    "january": 1, "february": 2, "march": 3, "april": 4, "june": 6,
    "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "december": 12,
    "januari": 1, "februari": 2, "maret": 3, "april": 4, "mei": 5, "juni": 6,
    "juli": 7, "agustus": 8, "september": 9, "oktober": 10, "november": 11, "desember": 12,
}

# Column name aliases
COLUMN_ALIASES = {
    "date": ["date", "tanggal", "tgl", "time", "timestamp", "waktu", "tarikh"],
    "open": ["open", "opening", "pembukaan", "buka"],
    "high": ["high", "highest", "tertinggi", "max", "maximum"],
    "low": ["low", "lowest", "terendah", "min", "minimum"],
    "close": ["close", "closing", "penutupan", "price", "harga", "last", "adj close", "adjusted close"],
    "volume": ["volume", "vol", "vol.", "volume.", "trading volume", "vol total", "jumlah"],
}


@dataclass
class CleanResult:
    """Result of cleaning a single CSV file."""
    rows: List[Dict]
    row_count: int
    delimiter: str
    date_format: str
    source: str
    output_name: str
    error: Optional[str] = None


def _clean_number(s: str) -> str:
    """Remove quotes, thousand separators, currency symbols. Keep last dot as decimal."""
    if not s:
        return ""
    s = s.replace('"', "").replace(",", "")
    # Handle European format "3.170,00" → remove dots, keep comma as decimal? 
    # Simplified: remove all non-digit/dot/minus, keep last dot
    s = re.sub(r"[^0-9.\-]", "", s)
    # If multiple dots, keep only the last one
    parts = s.split(".")
    if len(parts) > 2:
        s = "".join(parts[:-1]) + "." + parts[-1]
    return s.strip()


def _parse_date(date_str: str) -> Tuple[Optional[str], str]:
    """
    Parse a date string in various formats.
    Returns (normalized_date "YYYY-MM-DD", detected_format_name).
    """
    date_str = date_str.replace('"', "").strip()

    # Unix timestamp (10 digits = seconds, 13 = milliseconds)
    if re.match(r"^\d{10}$", date_str):
        from datetime import datetime, timezone
        d = datetime.fromtimestamp(int(date_str), tz=timezone.utc)
        return d.strftime("%Y-%m-%d"), "Unix timestamp"
    if re.match(r"^\d{13}$", date_str):
        from datetime import datetime, timezone
        d = datetime.fromtimestamp(int(date_str) / 1000, tz=timezone.utc)
        return d.strftime("%Y-%m-%d"), "Unix timestamp (ms)"

    # ISO format: 2026-08-21
    if re.match(r"^\d{4}-\d{2}-\d{2}$", date_str):
        return date_str, "YYYY-MM-DD"
    # ISO with time: 2026-08-21T00:00:00
    if re.match(r"^\d{4}-\d{2}-\d{2}T", date_str):
        return date_str[:10], "ISO 8601"

    # MMM d, yyyy: "Aug 21, 2026"
    m = re.match(r"^([A-Za-z]+)\s+(\d{1,2}),?\s+(\d{4})$", date_str)
    if m:
        mon = MONTH_MAP.get(m.group(1).lower()[:3])
        if mon:
            return f"{m.group(3)}-{mon:02d}-{int(m.group(2)):02d}", "MMM d, yyyy"

    # d MMM yyyy: "21 Aug 2026"
    m = re.match(r"^(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})$", date_str)
    if m:
        mon = MONTH_MAP.get(m.group(2).lower()[:3])
        if mon:
            return f"{m.group(3)}-{mon:02d}-{int(m.group(1)):02d}", "d MMM yyyy"

    # DD/MM/YYYY or MM/DD/YYYY
    m = re.match(r"^(\d{1,2})/(\d{1,2})/(\d{4})$", date_str)
    if m:
        p1, p2, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if p1 > 12:
            day, mon = p1, p2
        elif p2 > 12:
            mon, day = p1, p2
        else:
            mon, day = p1, p2
        return f"{y}-{mon:02d}-{day:02d}", "DD/MM/YYYY"

    # DD.MM.YYYY
    m = re.match(r"^(\d{1,2})\.(\d{1,2})\.(\d{4})$", date_str)
    if m:
        p1, p2, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if p1 > 12:
            day, mon = p1, p2
        elif p2 > 12:
            mon, day = p1, p2
        else:
            day, mon = p1, p2
        return f"{y}-{mon:02d}-{day:02d}", "DD.MM.YYYY"

    # YYYYMMDD
    m = re.match(r"^(\d{4})(\d{2})(\d{2})$", date_str)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}", "YYYYMMDD"

    return None, "Unknown"


def _find_columns(header: List[str]) -> Dict[str, int]:
    """Map header names to column indices using aliases."""
    col_map = {k: -1 for k in COLUMN_ALIASES}
    for i, h in enumerate(header):
        hl = h.lower().strip()
        for key, aliases in COLUMN_ALIASES.items():
            if col_map[key] != -1:
                continue
            for alias in aliases:
                if hl == alias or hl.startswith(alias):
                    col_map[key] = i
                    break
        # Special: adj close → close
        if hl in ("adj close", "adjusted close") and col_map["close"] == -1:
            col_map["close"] = i
        if hl == "price" and col_map["close"] == -1:
            col_map["close"] = i
    return col_map


def _detect_source(header: List[str]) -> str:
    """Detect data source from header."""
    h_lower = [h.lower() for h in header]
    if "adj close" in h_lower:
        return "Yahoo Finance"
    if "price" in h_lower or "change %" in h_lower:
        return "Investing.com"
    if "time" in h_lower or "timestamp" in h_lower:
        return "TradingView"
    if "tanggal" in h_lower:
        return "RTI/Indonesia"
    return "Unknown"


def clean_csv_text(text: str, filename: str = "input.csv") -> CleanResult:
    """
    Clean a CSV text string into standard OHLCV format.
    """
    # Remove BOM
    text = text.lstrip("\ufeff")

    # Detect delimiter
    comma_count = text.count(",")
    semicolon_count = text.count(";")
    delimiter = ";" if semicolon_count > comma_count else ","

    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    if len(lines) < 2:
        return CleanResult([], 0, delimiter, "Unknown", "Unknown", filename, error="Not enough rows")

    # Parse header
    header = [h.replace('"', "").strip() for h in lines[0].split(delimiter)]
    col_map = _find_columns(header)

    # Validate required columns
    missing = [k.capitalize() for k, v in col_map.items() if v == -1 and k != "volume"]
    if missing:
        return CleanResult([], 0, delimiter, "Unknown", "Unknown", filename,
                          error=f"Missing columns: {', '.join(missing)}")

    source = _detect_source(header)
    date_format = "Unknown"
    rows = []

    for line in lines[1:]:
        line = line.strip()
        if not line:
            continue
        fields = line.split(delimiter)
        if len(fields) < 5:
            continue

        date_str = fields[col_map["date"]].replace('"', '').strip()
        date_result, fmt = _parse_date(date_str)
        if date_result is None:
            continue
        if date_format == "Unknown":
            date_format = fmt

        try:
            open_v = float(_clean_number(fields[col_map["open"]]))
            high_v = float(_clean_number(fields[col_map["high"]]))
            low_v = float(_clean_number(fields[col_map["low"]]))
            close_v = float(_clean_number(fields[col_map["close"]]))
        except (ValueError, IndexError):
            continue

        vol_str = _clean_number(fields[col_map["volume"]]) if col_map["volume"] >= 0 and col_map["volume"] < len(fields) else ""
        try:
            volume = int(float(vol_str)) if vol_str else 0
        except ValueError:
            volume = 0

        # Validate
        if open_v <= 0 or high_v <= 0 or low_v <= 0 or close_v <= 0:
            continue
        if low_v > high_v:
            continue

        rows.append({
            "date": date_result,
            "open": open_v,
            "high": high_v,
            "low": low_v,
            "close": close_v,
            "volume": volume,
        })

    if not rows:
        return CleanResult([], 0, delimiter, date_format, source, filename,
                          error="No valid data rows (check date format or column mapping)")

    # Sort ascending
    rows.sort(key=lambda r: r["date"])

    # Remove duplicates
    seen = set()
    unique_rows = []
    for row in rows:
        if row["date"] not in seen:
            seen.add(row["date"])
            unique_rows.append(row)

    # Generate output filename
    output_name = filename
    for pattern, repl in [
        (r"-history\.csv$", "_cleaned.csv"),
        (r"\.csv$", "_cleaned.csv"),
        (r"\.txt$", "_cleaned.csv"),
    ]:
        new_name = re.sub(pattern, repl, output_name, flags=re.IGNORECASE)
        if new_name != output_name:
            output_name = new_name
            break
    if output_name == filename:
        output_name = re.sub(r"\.[^.]+$", "_cleaned.csv", filename)

    _log.info("cleaned | file=%s rows=%d delimiter=%s date=%s source=%s",
              filename, len(unique_rows), delimiter, date_format, source)

    return CleanResult(
        rows=unique_rows,
        row_count=len(unique_rows),
        delimiter=delimiter,
        date_format=date_format,
        source=source,
        output_name=output_name,
    )


def clean_csv_file(input_path: str, output_dir: str = ".") -> CleanResult:
    """Clean a CSV file and write the result to output_dir."""
    with open(input_path, "r", encoding="utf-8-sig") as f:
        text = f.read()

    filename = os.path.basename(input_path)
    result = clean_csv_text(text, filename)

    if result.error:
        return result

    # Write output
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, result.output_name)
    write_cleaned_csv(result.rows, output_path)

    return result


def write_cleaned_csv(rows: List[Dict], path: str):
    """Write cleaned rows to CSV file."""
    with open(path, "w", encoding="utf-8") as f:
        f.write("Date,Open,High,Low,Close,Volume\n")
        for r in rows:
            f.write(f"{r['date']},{r['open']},{r['high']},{r['low']},{r['close']},{r['volume']}\n")
    _log.debug("written | path=%s rows=%d", path, len(rows))


def rows_to_csv_string(rows: List[Dict]) -> str:
    """Convert cleaned rows to CSV string."""
    lines = ["Date,Open,High,Low,Close,Volume"]
    for r in rows:
        lines.append(f"{r['date']},{r['open']},{r['high']},{r['low']},{r['close']},{r['volume']}")
    return "\n".join(lines) + "\n"
