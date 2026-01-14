import uuid

from api.services.files import FilesService


def test_speech_file():
    book_id = uuid.uuid4()
    book_only = FilesService.speech_filename(book_id)
    assert book_only.startswith(str(book_id))
    assert book_only.endswith("/speech")

    file_name = "test.ext"
    with_file_name = FilesService.speech_filename(book_id, file_name)
    assert with_file_name.startswith(str(book_id))
    assert with_file_name.endswith(f"/speech/{file_name}")
