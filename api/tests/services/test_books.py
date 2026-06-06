import uuid

from api.services.books import BookService

books_service = BookService(None, None, None)


class TestBooksService:
    def test_master_playlist(self):
        id = uuid.UUID("84efd0c9-80b5-46f4-bf13-44b3726baf25")

        playlist = books_service._generate_master_playlist(id, "kokoro", "am_michael")
        print()
        print(playlist)
