import logging

from api.utils.text import ParagraphBuilder, RemoveKeywords, CleanupPipeline, SingleWhitespace, Quotes, LineReader, \
    ParagraphBuilderV2, pages_to_paragraphs, paragraphs_to_sections
from pypdf import PdfReader
from tests.utils.pdf import create_pdf

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


def test_line_reader():
    pdf_reader = PdfReader(create_pdf([["First line", "Another line"], ["Second page"]]))
    pages = [p.extract_text() for p in pdf_reader.pages]
    line_reader = LineReader(pages, CleanupPipeline([]))

    expected = [(0, "First line"), (0, "Another line"), (1, "Second page")]
    current = 0

    while line_reader.has_next():
        assert line_reader.next() == expected[current]
        current += 1


def test_paragraph_builder_v2():
    pb = ParagraphBuilderV2()

    assert pb._starts_with_lower("-from")
    assert pb._starts_with_lower("–from")
    assert pb._starts_with_lower("she")
    assert pb._starts_with_lower("test")
    assert not pb._starts_with_lower("- test")
    assert not pb._starts_with_lower("He")
    assert not pb._starts_with_lower("---")


def test_pages_to_paragraphs():
    pages = [
        """A beginning is the time for taking the most delicate care that
the balances are correct. This every sister of the Bene Gesserit
knows. To begin your study of the life of Muad'Dib, then, take""",
        """care that you first place him in his time: born in the 57th year of
the Padishah Emperor, Shaddam IV. And take the most special
care that you locate Muad'Dib in his place: the planet Arrakis.
Do not be deceived by the fact that he was bom on Caladan and
lived his first fifteen years there. Arrakis, the planet known as
Dune, is forever his place."""
    ]

    paragraphs = pages_to_paragraphs(pages)
    assert paragraphs[0] == (0, "A beginning is the time for taking the most delicate care that the balances are correct. This every sister of the Bene Gesserit knows. To begin your study of the life of Muad'Dib, then, take care that you first place him in his time: born in the 57th year of the Padishah Emperor, Shaddam IV. And take the most special care that you locate Muad'Dib in his place: the planet Arrakis.")
    assert paragraphs[1] == (1, "Do not be deceived by the fact that he was bom on Caladan and lived his first fifteen years there. Arrakis, the planet known as Dune, is forever his place.")
