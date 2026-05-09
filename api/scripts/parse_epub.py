import os
from zipfile import ZipFile

dir_with_books = "../../out/epub"

def all_files(dir: str) -> list[str]:
    files = []
    for filename in os.listdir(dir):
        if filename.endswith(".epub"):
            abs_file_path = os.path.abspath(os.path.join(dir, filename))
            files.append(abs_file_path)
    return files

def get_root_file():
    pass

if __name__ == "__main__":
    all_books = all_files(dir_with_books)
    print(f"Found {len(all_books)} books: \n  {"\n  ".join(all_books)}")

    # Start processing each file
    for book_file in all_books:
        print("Processing:", book_file)
        with ZipFile(book_file) as epubf:
            pass


    print("Done...")
