import time

from scripts.auth import session


def load_images(book_id, attempts=10):
    images = []
    for i in range(attempts):
        images = request.get(f"https://nnarrator.eu/api/books/{book_id}/images").json()
        if len(images) > 0:
            return images
        else:
            time.sleep(3)

    return images


if __name__ == "__main__":
    request = session()

    books = request.get("https://nnarrator.eu/api/books/").json()
    print(books)

    # For each book without cover, extract images, load images, set cover.

    skip_ids = {"7aff0995-5a21-414f-bff7-c5e6774dc050"}

    for book_ind, book in enumerate(books):
        print(f"Processing book {book_ind+1}/{len(books)}... {book['id']} {book['title']}")
        if book["cover"]:
            print(f"Book {book['id']} already has a cover: {book['cover']}, skipping...")
            continue

        if book['id'] in skip_ids:
            print(f"Skipping book {book['id']} {book['cover']}...")
            continue

        # Check if already has images:
        book_images = load_images(book['id'], 1)
        if len(book_images) == 0:
            print(f"Triggering image extraction for book {book['title']}...")
            request.post(f"https://nnarrator.eu/api/processing/{book['id']}/extract-images")
            time.sleep(5)

            # Reload images
            book_images = load_images(book['id'], 30)
            if len(book_images) == 0:
                raise Exception(f"No images found for book {book['title']} after extraction.")

        print(f"Setting {book_images[0]} as cover for book {book['title']}...")
        request.post(f"https://nnarrator.eu/api/books/{book['id']}/metadata/cover",
                     json={"file_path": book_images[0]})

        time.sleep(0.5)

    print("Done...")
