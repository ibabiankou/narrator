import json
import logging
import os

from requests import HTTPError

from scripts.client import NNarrator

LOG = logging.getLogger(__name__)


def all_files(dir: str) -> list[str]:
    dir = os.path.expanduser(dir)
    dir = os.path.abspath(dir)
    LOG.info("Scanning %s for epub files...", dir)
    files = []
    for filename in os.listdir(dir):
        if filename.endswith(".epub"):
            abs_file_path = os.path.join(dir, filename)
            files.append(abs_file_path)
    return files


if __name__ == "__main__":
    narrator = NNarrator("https://laptop.ggnt.eu:4200/api/")

    all_books = []
    all_books.extend(all_files("../../out/epub"))
    all_books.extend(all_files("~/data"))
    all_books.sort()

    subset = all_books

    LOG.info("Found %s books but will process only %s.", len(all_books), len(subset))
    LOG.info("  %s", "\n  ".join(all_books))
    for book in subset:
        LOG.info("Uploading %s", book)
        book_size = os.path.getsize(book)
        if book_size > 15 * 1024 * 1024:
            LOG.info("Skipping too large book '%s'. Actual size: %sMB", book, book_size / 1024 / 1024)
            continue
        try:
            narrator.procurement_upload(book)
        except HTTPError as e:
            if e.response.status_code == 400:
                LOG.error(json.dumps(e.response.json(), indent=2))
                continue
            raise e

    LOG.info("Done...")
