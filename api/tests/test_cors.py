import re

from api.main import CORS_REGEX


def test_domains():
    pattern = re.compile(CORS_REGEX)

    allowed = ["https://local.ggnt.eu:4200", "https://narrator.in.ggnt.eu", "local.ggnt.eu:4200", "local.ggnt.eu"]
    for origin in allowed:
        assert pattern.fullmatch(origin) is not None

    forbidden = ["https://google.com"]
    for origin in forbidden:
        assert pattern.fullmatch(origin) is None
