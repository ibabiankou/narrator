import re
import uuid

from stdnum import isbn
from typing import Tuple

def normalize_identifier(raw_id: str) -> Tuple[str, str]:
    """
    Normalizes a metadata identifier into a (type, value) pair.
    Returns ('unknown', original) if no pattern matches.
    """
    if not raw_id:
        raise ValueError("Identifier cannot be empty")

    # 1. Basic Cleanup
    # We work with lowercase for prefix matching, but preserve
    # casing for the core value initially.
    original = raw_id.strip()
    clean_id = original.lower()

    # 2. Strip common URN/Tag prefixes
    # Order matters: strip longer prefixes first
    prefixes = [
        'urn:isbn:', 'isbn:',
        'urn:uuid:', 'uuid:',
        'urn:asin:', 'asin:',
        'urn:eidr:', 'eidr:',
        'urn:'
    ]

    core_value = original
    for prefix in prefixes:
        if clean_id.startswith(prefix):
            core_value = original[len(prefix):].strip()
            break

    # 3. ISBN Normalization
    # stdnum.isbn.is_valid handles both ISBN-10 and ISBN-13
    if isbn.is_valid(core_value):
        # Convert everything to ISBN-13 to ensure 10-digit and 13-digit
        # versions of the same book match. Also remove any separators
        normalized_isbn = isbn.compact(core_value, convert=True)
        return "isbn", normalized_isbn

    # Try searching for ISBN-10 or ISBN-13 like substring with regex.
    isbn_match = re.search(r'(\d{3}-\d-\d{3}-\d{5}-\d|\d{13}|\d{10}|\d{9}X)', core_value, re.IGNORECASE)
    if isbn_match:
        isbn_maybe = isbn_match.group(1)
        if isbn.is_valid(isbn_maybe):
            normalized_isbn = isbn.compact(isbn_maybe, convert=True)
            return "isbn", normalized_isbn

    # 4. ASIN Identification (B-series)
    # 10 chars, alphanumeric, usually starts with B
    # We uppercase ASINs as per Amazon standard
    asin_match = re.match(r'^(B[0-9A-Z]{9})$', core_value, re.IGNORECASE)
    if asin_match:
        return "asin", asin_match.group(1).upper()

    # 5. UUID Normalization
    uuid_pattern = r'[a-f0-9]{8}-?[a-f0-9]{4}-?[a-f0-9]{4}-?[a-f0-9]{4}-?[a-f0-9]{12}'
    uuid_match = re.search(uuid_pattern, core_value, re.IGNORECASE)
    if uuid_match:
        try:
            parsed_uuid = uuid.UUID(core_value)
            return "uuid", str(parsed_uuid).lower()
        except ValueError:
            pass

    # 6. URL Identification
    if core_value.lower().startswith(('http://', 'https://')):
        return "url", core_value.lower().rstrip('/')

    # 7. Generic Tagged IDs (e.g., "google:12345", "calibre:1")
    if ":" in core_value:
        tag, val = core_value.split(":", 1)
        return tag.lower(), val.strip()

    return "unknown", core_value
