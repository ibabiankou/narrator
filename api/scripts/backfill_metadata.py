
from scripts.auth import session


if __name__ == "__main__":
    request = session()

    books = request.get("https://nnarrator.eu/api/books/").json()
    print(books)

    print("Done...")
