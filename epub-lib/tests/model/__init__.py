from xmldiff.main import diff_texts


# noinspection PyTypeChecker
def assert_no_diff(left, right):
    diffs = diff_texts(left, right)
    if diffs:
        print()
        print(diffs)
        print("Left:")
        print(left)
        print("Right:")
        print(right)
    assert len(diffs) == 0
