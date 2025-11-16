import argparse
import csv
import os
import sys
from typing import List

# Reuse the email validation logic from keep_first_email.py
try:
    from keep_first_email import is_valid_email_candidate
except Exception as exc:  # pragma: no cover
    print(f"Error: Could not import validation from keep_first_email.py: {exc}", file=sys.stderr)
    sys.exit(1)


def compute_default_output_path(input_path: str) -> str:
    base, ext = os.path.splitext(input_path)
    return f"{base}_rows_removed{ext or '.csv'}"


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


def remove_rows_with_invalid_email(
    input_csv_path: str,
    output_csv_path: str,
    email_column: str = "email",
    drop_empty: bool = False,
) -> None:
    total_rows = 0
    kept_rows = 0
    dropped_invalid = 0
    dropped_empty = 0

    with open(input_csv_path, mode="r", newline="", encoding="utf-8") as infile:
        reader = csv.DictReader(infile)
        validate_column_exists(reader.fieldnames, email_column)
        fieldnames = reader.fieldnames or []

        with open(output_csv_path, mode="w", newline="", encoding="utf-8") as outfile:
            writer = csv.DictWriter(outfile, fieldnames=fieldnames)
            writer.writeheader()

            for row in reader:
                total_rows += 1
                email_value = (row.get(email_column, "") or "").strip()

                if email_value == "":
                    if drop_empty:
                        dropped_empty += 1
                        continue
                    writer.writerow(row)
                    kept_rows += 1
                    continue

                if not is_valid_email_candidate(email_value):
                    dropped_invalid += 1
                    continue

                writer.writerow(row)
                kept_rows += 1

    print(
        f"Processed {total_rows} data rows. Kept {kept_rows}. "
        f"Dropped {dropped_invalid} invalid-email rows"
        + (f" and {dropped_empty} empty-email rows" if drop_empty else "")
        + "."
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Remove rows from a CSV where the email column is invalid/asset-like."
    )
    parser.add_argument("input_csv", help="Path to the input CSV file")
    parser.add_argument(
        "-c", "--column", default="email", help="Email column name (default: email)"
    )
    parser.add_argument(
        "-o",
        "--output",
        help=(
            "Path to write the filtered CSV. Defaults to '<input>_rows_removed.csv' in the same folder."
        ),
    )
    parser.add_argument(
        "--drop-empty",
        action="store_true",
        help="Also drop rows where the email column is empty",
    )

    args = parser.parse_args()

    input_path = args.input_csv
    if not os.path.isfile(input_path):
        print(f"Error: File not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    output_path = args.output or compute_default_output_path(input_path)
    remove_rows_with_invalid_email(
        input_csv_path=input_path,
        output_csv_path=output_path,
        email_column=args.column,
        drop_empty=args.drop_empty,
    )
    print(f"Wrote filtered CSV to: {output_path}")


if __name__ == "__main__":
    main()




