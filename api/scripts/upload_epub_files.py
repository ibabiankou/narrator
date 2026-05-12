import logging
import os

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

    subset = all_books[:50]

    LOG.info("Found %s books but will process only %s.", len(all_books), len(subset))
    LOG.info("  %s", "\n  ".join(all_books))
    for book in subset:
        LOG.info("Uploading %s", book)
        narrator.procurement_upload(book)

    print("Done...")
