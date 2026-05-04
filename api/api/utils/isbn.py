import re
from typing import Optional


def clean_isbn(value: str) -> str:
    """Remove any character that is NOT 0-9 or X (case-insensitive), and convert to uppercase."""
    return re.sub(r'[^0-9X]', '', value, flags=re.IGNORECASE).upper()


def isbn10_to_isbn13(isbn10: str) -> str:
    """Convert an ISBN10 to ISBN13."""

    if len(isbn10) != 10:
        raise ValueError("Input must be a 10-digit ISBN.")

    core_digits = "978" + isbn10[:-1]

    # Calculate the ISBN-13 check digit. Weights are alternating 1 and 3.
    total = 0
    for i, digit in enumerate(core_digits):
        weight = 1 if i % 2 == 0 else 3
        total += int(digit) * weight

    # Check digit is (10 - (total % 10)) % 10
    remainder = total % 10
    check_digit = (10 - remainder) % 10

    return core_digits + str(check_digit)


def isbn13_to_isbn10(isbn13: str) -> Optional[str]:
    """Convert an ISBN13 to ISBN10 if possible."""

    if len(isbn13) != 13:
        raise ValueError("Input must be a 13-digit ISBN.")

    # Only ISBN-13s starting with 978 can be converted to ISBN-10
    if not isbn13.startswith("978"):
        return None

    # Strip the '978' prefix and the check digit
    core_digits = isbn13[3:12]

    # Calculate the ISBN-10 check digit using Modulo 11
    # Weights go from 10 down to 2 for the first 9 digits
    total = 0
    for i, digit in enumerate(core_digits):
        weight = 10 - i
        total += int(digit) * weight

    # The check digit makes the total sum divisible by 11
    remainder = total % 11
    check_val = (11 - remainder) % 11

    # Handle the 'X' case (where check value is 10)
    if check_val == 10:
        check_digit = "X"
    else:
        check_digit = str(check_val)

    return core_digits + check_digit


def expand_isbns(isbns: list[str]) -> list[str]:
    """For each ISBN10 add equivalent ISBN13, and the other way around."""
    expanded_isbns = []
    for isbn in isbns:
        expanded_isbns.append(isbn)
        if len(isbn) == 10:
            isbn13 = isbn10_to_isbn13(isbn)
            expanded_isbns.append(isbn13)
            continue

        if len(isbn) == 13:
            isbn10_maybe = isbn13_to_isbn10(isbn)
            if isbn10_maybe is not None:
                expanded_isbns.append(isbn10_maybe)
                continue

    return expanded_isbns
