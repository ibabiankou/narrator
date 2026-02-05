import re
from typing import Protocol

from pypdf import PdfReader

from api import get_logger

LOG = get_logger(__name__)


class ParagraphBuilder:
    """A buffer using simple logic to guess if the text represents a single paragraph."""

    def __init__(self):
        self.page_index = None
        self.text = ""
        self.stack = []
        # Should only be true if the last char was either one of [.!?] or one of the closing quotes.
        self._is_incomplete_sentence = False

        self._matching_quotes = [('“', '”'), ('«', '»'), ('‹', '›')]
        self._opening_quotes = [o for o, c in self._matching_quotes]
        self._closing_quotes = [c for o, c in self._matching_quotes]
        self._quote_dict = {c: o for o, c in self._matching_quotes}
        # Ignore quotes condition if we got some clearly invalid state.
        self._ignore_quotes = False

        self._sentence_finishers = '.!?'

    def _is_empty(self):
        return len(self.text.strip()) == 0

    def need_more_text(self) -> bool:
        """Returns True if the text is most likely an incomplete paragraph."""
        return self._is_empty() or (not self._ignore_quotes and len(self.stack) != 0) or self._is_incomplete_sentence

    def append(self, line: tuple[int, str]):
        """Append a line of text."""
        LOG.debug("Appending line: \n%s", line)

        if self.page_index is None or (self.page_index != line[0] and self._is_empty()):
            self.page_index = line[0]

        if len(self.text) > 0:
            self.text += " "

        text_index = len(self.text)
        line_index = 0
        self.text += line[1]
        LOG.debug("Full text: \n%s", self.text)

        for character in line[1]:
            if not self._ignore_quotes:
                if character in self._opening_quotes:
                    LOG.debug("%03d Got opening quote: %s", line_index, character)
                    if character in self.stack:
                        self._ignore_quotes = True
                        LOG.warning("The same opening quote is already in stack. Ignoring quotes going forward...")
                        continue
                    self.stack.append(character)
                if character in self._closing_quotes:
                    if len(self.stack) == 0:
                        LOG.warning("Invalid quote state in a paragraph. Got closing quote with an empty stack."
                                    "Position: %s text: \n%s", text_index, self.text)
                        # TODO: Don't know what to do with this... Maybe write those cases somewhere,
                        #  so that I can check them later?
                        self._ignore_quotes = True
                        LOG.warning("Ignoring quotes going forward...")
                        continue
                    if self.stack[-1] == self._quote_dict[character]:
                        LOG.debug("%03d Got matching quotes, popping the stack. Also assuming sentence is complete.",
                                  line_index)
                        self.stack.pop()
                        # Assume that a properly quoted section represents a complete sentence.
                        self._is_incomplete_sentence = False
                    else:
                        LOG.warning("Invalid quote state in a paragraph. Got mismatching opening and closing quotes."
                                    "Stack: %s Position: %s text: \n%s", self.stack, text_index, self.text)
                        # TODO: Don't know what to do with this... Maybe write those cases somewhere,
                        #  so that I can check them later?
                        self._ignore_quotes = True
                        LOG.warning("Ignoring quotes going forward...")
                        continue

            if self._is_incomplete_sentence and character in self._sentence_finishers:
                self._is_incomplete_sentence = False
                LOG.debug("%03d Got sentence finisher.", line_index)
            # If it's not a whitespace or quote or sentence finisher, then flip is incomplete sentence
            if character not in [' ', *self._opening_quotes, *self._closing_quotes, *self._sentence_finishers]:
                self._is_incomplete_sentence = True
                LOG.debug("%03d Incomplete sentence.", line_index)

            text_index += 1
            line_index += 1

        LOG.debug("Need more text: %s", self.need_more_text())

    def build(self) -> tuple[int, str]:
        return self.page_index, self.text.strip()


class SectionBuilder:
    def __init__(self, target_length: int = 500):
        self.text = ""
        self.page_index = None
        self.target_length = target_length

    def need_more_text(self) -> bool:
        return len(self.text) < self.target_length

    def is_empty(self):
        return len(self.text.strip()) == 0

    def append(self, line: tuple[int, str]):
        if self.page_index is None or (self.page_index != line[0] and self.is_empty()):
            self.page_index = line[0]

        if len(line[1].strip()) > 0:
            if not self.is_empty():
                self.text += "\n"
            self.text += line[1]

    def build(self):
        if len(self.text) > self.target_length * 2:
            LOG.warning("Length of the section is significantly longer than the target.")
            LOG.warning("Section text: \n%s", self.text)
        return {"page_index": self.page_index, "content": self.text}


class LineTransformer(Protocol):
    def __call__(self, line: str) -> str:
        """Modify a line of raw text and return the result."""
        pass


class RemoveKeywords(LineTransformer):
    key_words = ["OceanofPDF.com", "OceanofPDF .com", "\0"]

    def __call__(self, line: str) -> str:
        for key_word in self.key_words:
            line = line.replace(key_word, "")
        return line


class SingleWhitespace(LineTransformer):
    expression = re.compile(r"\s+")

    def __call__(self, line: str) -> str:
        return self.expression.sub(" ", line)


class Quotes(LineTransformer):
    pairs = {
        "“": "\"",
        "”": "\"",
        "«": "\"",
        "»": "\"",
        "‹": "'",
        "›": "'",
        "‘": "'",
        "’": "'",
    }

    def __call__(self, line: str) -> str:
        for key, value in self.pairs.items():
            line = line.replace(key, value)
        return line


class CleanupPipeline:
    ALL_TRANSFORMERS = [RemoveKeywords(), SingleWhitespace(), Quotes()]

    def __init__(self, transformers: list[LineTransformer] = None):
        self.transformers: list[LineTransformer] = transformers or []

    def __call__(self, line: str) -> str:
        for transformer in self.transformers:
            line = transformer(line)
        return line


class LineReader:
    def __init__(self, pages: list[str], cleanup_pipeline: CleanupPipeline):
        self.cleanup_pipeline = cleanup_pipeline
        self.lines = self._read_lines(pages)
        self.line_index = 0

    def _read_lines(self, pages: list[str]):
        lines = []
        for page_index in range(len(pages)):
            page_lines = pages[page_index].splitlines()
            for raw_line in page_lines:
                line = self.cleanup_pipeline(raw_line)
                if len(line.strip()) > 0:
                    lines.append((page_index, line.strip()))
        return lines

    def has_next(self) -> bool:
        return self.line_index < len(self.lines)

    def next(self) -> tuple[int, str]:
        line = self.view_next()
        self.advance()
        return line

    def view_next(self):
        if self.has_next():
            line = self.lines[self.line_index]
            return line
        else:
            raise LookupError()

    def advance(self):
        self.line_index += 1


class ParagraphBuilderV2:
    """Builder that accepts lines of text until it seems to represent a paragraph."""

    def __init__(self):
        self.page_index = None
        self.text = ""

        # Number of lines within which more speech is expected.
        self.expect_more_speech = 0
        # Should be true if the last char was one of [.!?] optionally followed by a closing quote.
        self.is_complete_sentence = True

        self._sentence_finishers = '.!?'
        self._continuation_characters = '-–'

    def _starts_with_lower(self, line: str):
        if len(line) == 0:
            return False
        i = -1
        while i < len(line):
            i += 1
            if line[i] in self._continuation_characters:
                continue
            else:
                return line[i].islower()
        # TODO: Not quite sure what to do here...
        return False

    def offer(self, line: tuple[int, str]):
        starts_with_lower = self._starts_with_lower(line[1])

        if (len(self.text) > 0
                and self.expect_more_speech == 0
                and self.is_complete_sentence
                and not starts_with_lower):
            # We are done, so reject the offered line.
            return False

        # Update page index if needed
        if self.page_index is None:
            self.page_index = line[0]

        if len(self.text) > 0:
            self.text += " "
        self.text += line[1]

        # We accept the line, so process it

        if self.expect_more_speech > 0:
            self.expect_more_speech -= 1

        last_character = None
        for character in line[1]:
            if character == '"':
                # TODO: for now only treat comma as an indicator of continuing speech.
                if last_character == ',':
                    self.expect_more_speech += 2
                else:
                    self.expect_more_speech = 0

                continue

            self.is_complete_sentence = character in self._sentence_finishers
            last_character = character

        return True

    def build(self) -> tuple[int, str]:
        return self.page_index, self.text.strip()


def pages_to_paragraphs(pages: list[str]) -> list[tuple[int, str]]:
    line_reader = LineReader(pages, CleanupPipeline(CleanupPipeline.ALL_TRANSFORMERS))
    paragraphs = []
    while line_reader.has_next():
        paragraph_builder = ParagraphBuilderV2()
        while line_reader.has_next() and paragraph_builder.offer(line_reader.view_next()):
            line_reader.advance()
        paragraphs.append(paragraph_builder.build())

    return paragraphs

def paragraphs_to_sections(paragraphs: list[tuple[int, str]]) -> list[dict]:
    i = 0
    sections = []
    sb = SectionBuilder()
    while i < len(paragraphs):
        if sb.need_more_text():
            sb.append(paragraphs[i])
            i += 1
        else:
            sections.append(sb.build())
            sb = SectionBuilder()

    if not sb.is_empty():
        sections.append(sb.build())

    return sections
