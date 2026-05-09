import os

dir_with_books = "../../out/epub"

if __name__ == "__main__":
    for filename in os.listdir(dir_with_books):
        if filename.endswith(".epub"):
            print(f"Found EPUB file: {filename}")


    print("Done...")
