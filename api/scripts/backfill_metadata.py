import datetime

import time

from scripts.auth import session


def ts():
    return datetime.datetime.now(datetime.UTC).strftime('%Y-%m-%d %H:%M:%S')


def get_all_books():
    books = []
    keep_going = True
    page_index = 0
    page_size = 100
    # Go through all pages
    while keep_going:
        params = {
            "page_index": page_index,
            "size": page_size
        }
        books_page = request.get("https://nnarrator.eu/api/books/", params=params).json()
        books.extend(books_page["items"])
        keep_going = books_page["page_info"]["total"] > books_page["page_info"]["size"] * (books_page["page_info"]["index"] + 1)
        if keep_going:
            page_index += 1

    return books


if __name__ == "__main__":
    request = session()

    books = get_all_books()
    print(ts(), "Got", len(books), "books.")

    # In reversed oreder trigger metadata extraction for each book.
    reverse_books = list(reversed(books))
    for book in reverse_books:
        print(ts(), "Processing book", book["id"], book["title"])

        metadata_for_review = request.get(f"https://nnarrator.eu/api/books/{book['id']}/metadata/review").json()
        if len(metadata_for_review["metadata_candidates"]["candidates"]) > 0:
            print(ts(), "Skipping book", book["id"], book["title"], "already has metadata.")
            continue

        request.post(f"https://nnarrator.eu/api/processing/{book['id']}/extract-metadata")
        time.sleep(5)

    print(ts(), "Done...")
