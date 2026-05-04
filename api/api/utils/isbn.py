import re
from typing import Optional


def clean_isbn(value: str) -> str:
    """Remove any character that is NOT 0-9 or X (case-insensitive), and convert to uppercase."""
    return re.sub(r'[^0-9X]', '', value, flags=re.IGNORECASE).upper()

def check_digit_isbn10(isbn10: str) -> str:
    """Calculate the check digit for an ISBN-10 number."""
    if len(isbn10) < 9:
        raise ValueError("Input must be at least first 9 digits of ISBN-10.")

    total = 0
    for i, digit_char in enumerate(isbn10[:9]):
        weight = 10 - i
        total += int(digit_char) * weight

    remainder = total % 11
    check_val = (11 - remainder) % 11

    if check_val == 10:
        check_digit = "X"
    else:
        check_digit = str(check_val)

    return check_digit


def validate_isbn10(isbn10: str) -> bool:
    """Validate an ISBN-10 number."""
    if len(isbn10) != 10:
        return False
    if not isbn10[:-1].isdigit():
        return False
    if not (isbn10[-1].isdigit() or isbn10[-1].upper() == 'X'):
        return False

    return isbn10[-1].upper() == check_digit_isbn10(isbn10)


def check_digit_isbn13(isbn13: str) -> str:
    """Calculate the check digit for an ISBN-13 number."""
    if len(isbn13) < 12:
        raise ValueError("Input must be at least first 12 digits of ISBN-13.")

    total = 0
    for i, digit in enumerate(isbn13[:12]):
        weight = 1 if i % 2 == 0 else 3
        total += int(digit) * weight

    remainder = total % 10
    check_digit = (10 - remainder) % 10

    return str(check_digit)


def validate_isbn13(isbn13: str) -> bool:
    """Validate an ISBN-13 number."""
    if len(isbn13) != 13:
        return False
    if not isbn13.isdigit():
        return False

    return isbn13[-1] == check_digit_isbn13(isbn13)


def validate_isbn(isbn: str) -> bool:
    """
    Validate an ISBN-10 or ISBN-13 number.

    This function assumes the input has been cleaned by `clean_isbn`.
    """
    if len(isbn) == 10:
        return validate_isbn10(isbn)
    elif len(isbn) == 13:
        return validate_isbn13(isbn)
    else:
        return False


def isbn10_to_isbn13(isbn10: str) -> str:
    """Convert an ISBN10 to ISBN13."""

    if len(isbn10) != 10:
        raise ValueError("Input must be a 10-digit ISBN.")

    core_digits = "978" + isbn10[:-1]
    return core_digits + check_digit_isbn13(core_digits)


def isbn13_to_isbn10(isbn13: str) -> Optional[str]:
    """Convert an ISBN13 to ISBN10 if possible."""

    if len(isbn13) != 13:
        raise ValueError("Input must be a 13-digit ISBN.")

    # Only ISBN-13s starting with 978 can be converted to ISBN-10
    if not isbn13.startswith("978"):
        return None

    core_digits = isbn13[3:12]
    return core_digits + check_digit_isbn10(isbn13[3:])


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
