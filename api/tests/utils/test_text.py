import logging

from api.utils.text import ParagraphBuilder

logger = logging.getLogger(ParagraphBuilder.__module__)
logger.setLevel(logging.DEBUG)

def test_example():
    pb = ParagraphBuilder()

    text = """The shuttle vibrated underfoot, the air wavy from the heat
of the shuttle’s recent atmospheric entry. It was currently zipping along at
300 knots, the landscape below a brownish-green patchwork of farms."""
    lines = text.splitlines()

    for line in lines[:-1]:
        pb.append(line)
        assert pb.need_more_text()

    pb.append(lines[-1])
    assert not pb.need_more_text()
