from api.services.settings import recursive_patch


def test_recursive_patch1():
    current = {}
    patch = {
        "new": "val",
        "dict": {
            "k": "v"
        }
    }

    actual = recursive_patch(current, patch)
    assert "new" in actual and actual["new"] == "val" and "dict" in actual and actual["dict"]["k"] == "v"


def test_recursive_patch2():
    current = {
        "dict": {
            "k": "v"
        },
        "key": 1
    }
    patch = {
        "dict": {
            "k": "updated"
        },
        "key": {
            "nested": 2
        }
    }

    actual = recursive_patch(current, patch)
    assert actual["dict"]["k"] == "updated"
    assert isinstance(actual["key"], dict) and actual["key"]["nested"] == 2


def test_recursive_patch3():
    current = {
        "dict": {
            "k": "v"
        },
        "key": 1
    }
    patch = {
        "dict": {
            "k": None
        },
        "key": None
    }

    actual = recursive_patch(current, patch)
    assert "k" not in actual["dict"] and "key" not in actual
