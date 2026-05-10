from xmldiff.main import diff_texts


# noinspection PyTypeChecker
def assert_no_diff(left, right):
    assert len(diff_texts(left, right)) == 0
