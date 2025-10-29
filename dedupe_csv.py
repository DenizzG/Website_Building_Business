import argparse
import csv
import os
import sys
from typing import List, Set


def compute_default_output_path(input_path: str) -> str:
    base, ext = os.path.splitext(input_path)
    return f"{base}.deduped{ext or '.csv'}"


def validate_column_exists(fieldnames: List[str], column_name: str) -> None:
    if fieldnames is None:
        print("Error: Input CSV has no header row.", file=sys.stderr)
        sys.exit(1)
    if column_name not in fieldnames:
        print(
            f"Error: Column '{column_name}' not found. Available columns: {', '.join(fieldnames)}",
            file=sys.stderr,
        )
        sys.exit(1)


def dedupe_and_filter_rows(
    input_csv_path: str,
    output_csv_path: str,
    column_name: str,
) -> None:
    seen_values: Set[str] = set()
    total_rows = 0
    kept_rows = 0
    removed_empty = 0
    removed_dupes = 0

    with open(input_csv_path, mode="r", newline="", encoding="utf-8") as infile:
        reader = csv.DictReader(infile)
        validate_column_exists(reader.fieldnames, column_name)

        fieldnames = reader.fieldnames or []

        with open(output_csv_path, mode="w", newline="", encoding="utf-8") as outfile:
            writer = csv.DictWriter(outfile, fieldnames=fieldnames)
            writer.writeheader()

            for row in reader:
                total_rows += 1
                raw_value = row.get(column_name, "")
                value = (raw_value or "").strip()

                if value == "":
                    removed_empty += 1
                    continue

                if value in seen_values:
                    removed_dupes += 1
                    continue

                seen_values.add(value)
                writer.writerow(row)
                kept_rows += 1

    print(
        f"Processed {total_rows} data rows. Kept {kept_rows}. "
        f"Removed {removed_empty} empty and {removed_dupes} duplicates based on '{column_name}'."
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Remove rows with duplicate or empty values in a specified column of a CSV file."
        )
    )
    parser.add_argument("input_csv", help="Path to the input CSV file")
    parser.add_argument(
        "-c",
        "--column",
        required=True,
        help="Column name used to detect duplicates and empties",
    )
    parser.add_argument(
        "-o",
        "--output",
        help=(
            "Path to write the cleaned CSV. Defaults to '<input>.deduped.csv' in the same folder."
        ),
    )
    parser.add_argument(
        "--inplace",
        action="store_true",
        help="Overwrite the input CSV with the cleaned data",
    )

    args = parser.parse_args()

    input_path = args.input_csv
    if not os.path.isfile(input_path):
        print(f"Error: File not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    if args.inplace and args.output:
        print(
            "Error: Use either --inplace or --output, not both.",
            file=sys.stderr,
        )
        sys.exit(1)

    if args.inplace:
        temp_output = compute_default_output_path(input_path)
        dedupe_and_filter_rows(input_path, temp_output, args.column)
        try:
            os.replace(temp_output, input_path)
        except OSError as exc:
            print(
                f"Error: Failed to replace original file with cleaned file: {exc}",
                file=sys.stderr,
            )
            sys.exit(1)
        print(f"Overwrote input file with cleaned data: {input_path}")
    else:
        output_path = args.output or compute_default_output_path(input_path)
        dedupe_and_filter_rows(input_path, output_path, args.column)
        print(f"Wrote cleaned CSV to: {output_path}")


if __name__ == "__main__":
    main()


