import pytest
from api.utils.isbn import clean_isbn, isbn10_to_isbn13, isbn13_to_isbn10, expand_isbns


def test_clean_isbn():
    assert clean_isbn("978-0-306-40615-7") == "9780306406157"
    assert clean_isbn(" 0-306-40615-X ") == "030640615X"
    assert clean_isbn("ISBN: 0-306-40615-x") == "030640615X"
    assert clean_isbn("abc123def") == "123"


def test_isbn10_to_isbn13():
    assert isbn10_to_isbn13("0306406152") == "9780306406157"
    assert isbn10_to_isbn13("000000359X") == "9780000003591"
    with pytest.raises(ValueError):
        isbn10_to_isbn13("12345")


def test_isbn13_to_isbn10():
    assert isbn13_to_isbn10("9780306406157") == "0306406152"
    assert isbn13_to_isbn10("9780000003591") == "000000359X"
    assert isbn13_to_isbn10("9790306406156") is None
    with pytest.raises(ValueError):
        isbn13_to_isbn10("12345")


def test_expand_isbns():
    assert sorted(expand_isbns(["0306406152"])) == sorted(["0306406152", "9780306406157"])
    assert sorted(expand_isbns(["9780306406157"])) == sorted(["9780306406157", "0306406152"])
    assert expand_isbns(["9790306406156"]) == ["9790306406156"]
    assert sorted(expand_isbns(["0306406152", "9790306406156"])) == sorted(["0306406152", "9780306406157", "9790306406156"])
