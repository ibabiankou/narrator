import logging

from scripts.client import NNarrator

LOG = logging.getLogger(__name__)

if __name__ == "__main__":
    narrator = NNarrator("https://nnarrator.eu/api/")

    books = narrator.get_all_books()
    LOG.info("Got %s books", len(books))

    for book in books:
        LOG.info("Downloading %s %s", book.id, book.title)
        narrator.get_file(f"{book.id}/{book.pdf_file_name}", "/Users/ibabiankou/repos/narrator/out/books")

    print("Done...")
