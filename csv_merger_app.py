#!/usr/bin/env python
"""
Standalone CSV Merger CLI app.
Appends new raw data from Yahoo Finance to an existing cleaned CSV file.

Usage:
    python csv_merger_app.py -e existing_cleaned.csv -n new_raw1.csv new_raw2.csv -o output_dir
    python csv_merger_app.py --help
"""

import argparse
import sys
import os
import glob

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bei_swing_engine_v8.merger import merge_csv_files
from bei_swing_engine_v8.logging_config import setup_logging


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="SwingFlow v8.0 — CSV Merger (Append New Data)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python csv_merger_app.py -e BBRI_cleaned.csv -n BBRI_new.csv -o merged/
  python csv_merger_app.py -e BBRI_cleaned.csv --glob "new_data/*.csv" -o merged/
        """,
    )
    parser.add_argument("-e", "--existing", required=True, help="Existing cleaned CSV file")
    parser.add_argument("-n", "--new", nargs="*", default=[], help="New raw CSV file(s) to merge")
    parser.add_argument("--glob", dest="glob_pattern", default=None, help="Glob pattern for new files")
    parser.add_argument("-o", "--output-dir", default=".", help="Output directory")
    parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])

    args = parser.parse_args(argv)

    setup_logging(level=args.log_level)

    # Validate existing file
    if not os.path.exists(args.existing):
        print(f"ERROR: Existing file not found: {args.existing}", file=sys.stderr)
        sys.exit(1)

    # Collect new files
    new_files = list(args.new)
    if args.glob_pattern:
        new_files.extend(glob.glob(args.glob_pattern))

    if not new_files:
        parser.error("No new files specified. Use -n or --glob.")

    for f in new_files:
        if not os.path.exists(f):
            print(f"ERROR: New file not found: {f}", file=sys.stderr)
            sys.exit(1)

    os.makedirs(args.output_dir, exist_ok=True)

    print(f"SwingFlow v8.0 — CSV Merger")
    print(f"Existing: {args.existing}")
    print(f"New files: {len(new_files)}")
    print()

    result = merge_csv_files(args.existing, new_files, args.output_dir)

    if result.error:
        print(f"  [FAIL] {result.error}")
        sys.exit(1)

    print(f"  [ OK ] Merge complete")
    print(f"         Existing rows: {result.existing_count}")
    print(f"         New rows added: {result.new_count}")
    print(f"         Merged total:   {result.merged_count}")
    print(f"         Date range:    {result.first_date} to {result.last_date}")

    if result.new_dates:
        print(f"         New dates:     {', '.join(result.new_dates)}")
    else:
        print(f"         (No new data — all dates already exist)")

    print()
    print(f"Output: {os.path.join(os.path.abspath(args.output_dir), result.output_name)}")


if __name__ == "__main__":
    main()
