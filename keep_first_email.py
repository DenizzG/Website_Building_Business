import argparse
import csv
import os
import sys
from typing import List, Tuple
import re


def compute_default_output_path(input_path: str) -> str:
    base, ext = os.path.splitext(input_path)
    return f"{base}_first_email{ext or '.csv'}"


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


PRIORITY_LOCAL_PARTS: Tuple[str, ...] = (
    "info",
    "contact",
    "hello",
    "support",
    "help",
    "sales",
    "enquiries",
    "enquiry",
    "office",
    "team",
    "admin",
    "booking",
    "bookings",
    "service",
    "services",
)

REJECT_LOCAL_PART_KEYWORDS: Tuple[str, ...] = (
    "logo",
    "image",
    "photo",
    "icon",
    "banner",
    "asset",
    "noreply",
    "no-reply",
    "do-not-reply",
    "donotreply",
    "webmaster",  # often unattended
)

ASSET_EXTS: Tuple[str, ...] = (
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".svg",
    ".webp",
    ".ico",
    ".css",
    ".js",
    ".pdf",
)

EMAIL_RE = re.compile(r"^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}$", re.I)


def split_candidates(raw: str, delimiter: str) -> List[str]:
    raw = (raw or "").strip()
    if not raw:
        return []
    # Primary split by provided delimiter
    parts: List[str] = [p.strip() for p in raw.split(delimiter) if p.strip()]
    # If it looks like only one token but contains other common separators, widen split
    if len(parts) <= 1:
        widened = re.split(r"[;,|\s]+", raw)
        parts = [p.strip() for p in widened if p.strip()]
    return parts


def is_valid_email_candidate(candidate: str) -> bool:
    c = candidate.strip().strip(",;| ")
    if not c or "@" not in c:
        return False
    # Basic syntax check
    if not EMAIL_RE.match(c):
        return False
    # Domain must have a dot and not look like an asset filename
    domain = c.split("@", 1)[-1].lower()
    if "." not in domain:
        return False
    if any(domain.endswith(ext) for ext in ASSET_EXTS):
        return False
    # Reject domains with asset-like size/version patterns (e.g., 2x, 300x170, 2.0.2)
    if re.search(r"(?:^|[._-])\d+x(?:\d+)?(?:$|[._-])", domain):
        return False
    if re.search(r"(?:^|[._-])\d+(?:\.\d+)+(?:$|[._-])", domain):
        return False
    # Reject domains containing labels that are purely numeric (e.g., 2.0.2.ads -> labels '2','0','2')
    labels = [lbl for lbl in domain.split('.') if lbl]
    if any(lbl.isdigit() for lbl in labels[:-1]):  # ignore TLD
        return False
    # Reject obvious non-email local parts (e.g., logo@, image@)
    local = c.split("@", 1)[0].lower()
    if any(k in local for k in REJECT_LOCAL_PART_KEYWORDS):
        return False
    # Also reject local parts with asset-like size/version patterns
    if re.search(r"(?:^|[._-])\d+x(?:\d+)?(?:$|[._-])", local):
        return False
    if re.search(r"(?:^|[._-])\d+(?:\.\d+)+(?:$|[._-])", local):
        return False
    # Avoid common placeholders
    placeholders = {"example@example.com", "test@test.com", "email@domain.com"}
    if c.lower() in placeholders:
        return False
    return True


def email_priority_key(candidate: str, original_index: int) -> Tuple[int, int, int]:
    # Lower is better for sorting
    local = candidate.split("@", 1)[0].lower()
    # Exact match priority
    if local in PRIORITY_LOCAL_PARTS:
        priority_rank = 0
    # Startswith priority (e.g., info.london@)
    elif any(local.startswith(pfx + ".") or local.startswith(pfx + "+") or local.startswith(pfx + "-") for pfx in PRIORITY_LOCAL_PARTS):
        priority_rank = 1
    else:
        priority_rank = 2
    # Prefer shorter addresses slightly, then original order
    return (priority_rank, len(candidate), original_index)


def choose_best_email_from_cell(value: str, delimiter: str) -> str:
    candidates = split_candidates(value, delimiter)
    filtered: List[Tuple[str, int]] = []
    for idx, c in enumerate(candidates):
        c_norm = c.strip().strip(",;| ")
        if is_valid_email_candidate(c_norm):
            filtered.append((c_norm, idx))
    if not filtered:
        # Return original string (unchanged) if nothing valid found
        return (value or "").strip()
    # Sort by smart priority
    filtered.sort(key=lambda t: email_priority_key(t[0], t[1]))
    return filtered[0][0]


def keep_first_email(
    input_csv_path: str,
    output_csv_path: str,
    email_column: str = "email",
    delimiter: str = ";",
    drop_invalid: bool = False,
) -> None:
    total_rows = 0
    modified_rows = 0
    dropped_rows = 0

    with open(input_csv_path, mode="r", newline="", encoding="utf-8") as infile:
        reader = csv.DictReader(infile)
        validate_column_exists(reader.fieldnames, email_column)
        fieldnames = reader.fieldnames or []

        with open(output_csv_path, mode="w", newline="", encoding="utf-8") as outfile:
            writer = csv.DictWriter(outfile, fieldnames=fieldnames)
            writer.writeheader()

            for row in reader:
                total_rows += 1

                raw_value = row.get(email_column, "") or ""
                value = raw_value.strip()
                smart_email = choose_best_email_from_cell(value, delimiter)
                if smart_email != value:
                    modified_rows += 1
                # Optionally skip rows with invalid/asset-like email results
                if drop_invalid and not is_valid_email_candidate(smart_email):
                    dropped_rows += 1
                    continue
                row[email_column] = smart_email
                writer.writerow(row)

    if drop_invalid:
        print(
            f"Processed {total_rows} data rows. Modified {modified_rows}. Dropped {dropped_rows} invalid-email rows."
        )
    else:
        print(
            f"Processed {total_rows} data rows. Modified {modified_rows} rows with multiple emails."
        )


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Create a copy of a CSV where the specified email column keeps only the first semicolon-separated email."
        )
    )
    parser.add_argument("input_csv", help="Path to the input CSV file")
    parser.add_argument(
        "-c",
        "--column",
        default="email",
        help="Email column name (default: email)",
    )
    parser.add_argument(
        "-d",
        "--delimiter",
        default=";",
        help="Delimiter used between multiple emails (default: ';')",
    )
    parser.add_argument(
        "-o",
        "--output",
        help=(
            "Path to write the output CSV. Defaults to '<input>_first_email.csv' in the same folder."
        ),
    )
    parser.add_argument(
        "--drop-invalid",
        action="store_true",
        help="Drop rows where the resulting email is invalid/asset-like",
    )

    args = parser.parse_args()

    input_path = args.input_csv
    if not os.path.isfile(input_path):
        print(f"Error: File not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    output_path = args.output or compute_default_output_path(input_path)
    keep_first_email(
        input_csv_path=input_path,
        output_csv_path=output_path,
        email_column=args.column,
        delimiter=args.delimiter,
        drop_invalid=args.drop_invalid,
    )
    print(f"Wrote CSV with first emails to: {output_path}")


if __name__ == "__main__":
    main()


