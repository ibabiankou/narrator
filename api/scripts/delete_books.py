import time

from scripts.auth import session

if __name__ == "__main__":
    request = session("https://laptop.ggnt.eu:4200/api")

    book_ids = []
    print("Deleting", len(book_ids), "books:", book_ids)

    for id in book_ids:
        print("Deleting book", id)
        response = request.delete(f"/books/{id}")
        response.raise_for_status()
        time.sleep(1)

    print("Done...")
