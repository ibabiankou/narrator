import logging
import os

from scripts.client import NNarrator

LOG = logging.getLogger(__name__)

dir_with_books = "../../out/epub"


def all_files(dir: str) -> list[str]:
    files = []
    for filename in os.listdir(dir):
        if filename.endswith(".epub"):
            abs_file_path = os.path.abspath(os.path.join(dir, filename))
            files.append(abs_file_path)
    return files


if __name__ == "__main__":
    narrator = NNarrator("https://laptop.ggnt.eu:4200/api/")

    all_books = all_files(dir_with_books)
    LOG.info("Found %s books: \n  %s", len(all_books), "\n  ".join(all_books))
    for book in all_books:
        LOG.info("Uploading %s", book)
        narrator.procurement_upload(book)

    print("Done...")
