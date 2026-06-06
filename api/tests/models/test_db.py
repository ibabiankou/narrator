import uuid

from api.models import db


def test_base_as_dict():
    bid = uuid.uuid4()
    uid = uuid.uuid4()
    assert "id" not in db.PlaybackProgress(id=1, book_id=bid, user_id=uid, data={}).as_dict()

def test_base_as_dict_jsonb():
    progress = db.PlaybackProgress(book_id=uuid.uuid4(), data={"foo": "bar"})
    assert "data" in progress.as_dict()

def test_book_status_comparison():
    db_str = "ready"
    current_status = db.BookStatus(db_str)
    assert current_status == db.BookStatus.ready
    assert current_status >= db.BookStatus.ready
    assert current_status <= db.BookStatus.ready

    assert not current_status != db.BookStatus.ready
    assert not current_status < db.BookStatus.ready
    assert not current_status > db.BookStatus.ready

    assert current_status > db.BookStatus.ready_for_metadata_review
    assert current_status >= db.BookStatus.ready_for_metadata_review
    assert not current_status == db.BookStatus.ready_for_metadata_review
    assert not current_status < db.BookStatus.ready_for_metadata_review
    assert not current_status <= db.BookStatus.ready_for_metadata_review
