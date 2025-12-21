from api.models import db


def test_base_as_dict():
    assert "id" not in db.AudioTrack(id=1, book_id=2, section_id=3, status=db.AudioStatus.queued).as_dict()
