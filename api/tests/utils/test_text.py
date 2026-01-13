import logging

from api.utils.text import ParagraphBuilder, RemoveKeywords, CleanupPipeline, SingleWhitespace, Quotes

logger = logging.getLogger(ParagraphBuilder.__module__)
logger.setLevel(logging.DEBUG)


def test_example():
    pb = ParagraphBuilder()

    text = """The shuttle vibrated underfoot, the air wavy from the heat
of the shuttle’s recent atmospheric entry. It was currently zipping along at
300 knots, the landscape below a brownish-green patchwork of farms."""
    lines = text.splitlines()

    for line in lines[:-1]:
        pb.append((0, line))
        assert pb.need_more_text()

    pb.append((0, lines[-1]))
    assert not pb.need_more_text()


def test_imbalanced_quotes():
    pb = ParagraphBuilder()

    text = """“This is a prank of some sort, right? That Shalia woman drugs guys
and leaves them naked in a field then sends her friends to blackmail him or
something,” he said knowing that blackmail didn’t explain the body. “Is
this some Island of Dr. Moreau type thing?
“Adding unintelligible nonsense to your lies won’t make me believe
them,” Ena said contemptuously while shuffling uncomfortably. “And I
don’t believe your Shalia nonsense.”"""
    lines = text.splitlines()

    for line in lines[:-1]:
        pb.append((0, line))
        assert pb.need_more_text()

    pb.append((0, lines[-1]))
    assert not pb.need_more_text()


def test_empty_lines():
    pb = ParagraphBuilder()

    text = """ 
     
     """
    lines = text.splitlines()

    for line in lines:
        pb.append((0, line))
        assert pb.need_more_text()

    pb.append((1, "  "))

    assert pb.need_more_text()
    assert pb.build() == (1, "")


def test_remove_null_characters():
    test = "something with \0 character"

    assert "\0" in test

    transformer = RemoveKeywords()
    cleared = transformer(test)

    assert "\0" not in cleared


def test_empty_pipeline():
    text = f"""some text
    
    {RemoveKeywords.key_words[0]}
    more text"""

    pipeline = CleanupPipeline()
    cleaned_text = pipeline(text)

    assert text == cleaned_text


def test_whitespaces():
    text = """Book	One DUNE\n\nA	beginning   is"""

    transformer = SingleWhitespace()
    cleared = transformer(text)

    assert cleared == "Book One DUNE A beginning is"


def test_quotes():
    text = "from“A Child’s History of Muad’Dib” by «the» ‹Princess› ‘Irulan’"

    transformer = Quotes()
    cleared = transformer(text)

    assert cleared == "from\"A Child's History of Muad'Dib\" by \"the\" 'Princess' 'Irulan'"
