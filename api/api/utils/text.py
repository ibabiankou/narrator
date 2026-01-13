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
        # It takes around 25s to generate speech for 300 char snippet of text.
        self.text = ""
        self.page_index = None
        self.target_length = target_length

    def need_more_text(self) -> bool:
        return len(self.text) < self.target_length

    def is_empty(self):
        return len(self.text.strip()) > 0

    def append(self, line: tuple[int, str]):
        if self.page_index is None or (self.page_index != line[0] and self.is_empty()):
            self.page_index = line[0]

        if len(line[1].strip()) > 0:
            self.text += line[1] + "\n"

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


class CleanupPipeline:
    ALL_TRANSFORMERS = [RemoveKeywords(), SingleWhitespace()]
    def __init__(self, transformers: list[LineTransformer] = None):
        self.transformers: list[LineTransformer] = transformers or []

    def __call__(self, line: str) -> str:
        for transformer in self.transformers:
            line = transformer(line)
        return line


class LineReader:
    def __init__(self, pdf_reader: PdfReader, cleanup_pipeline: CleanupPipeline):
        self.cleanup_pipeline = cleanup_pipeline
        self.lines = self._read_lines(pdf_reader)
        self.line_index = 0

    def _read_lines(self, pdf_reader: PdfReader):
        lines = []
        pages = pdf_reader.pages
        for page_index in range(len(pages)):
            page_lines = pages[page_index].extract_text().splitlines()
            for raw_line in page_lines:
                line = self.cleanup_pipeline(raw_line)
                if len(line.strip()) > 0:
                    lines.append((page_index, line.strip()))
        return lines

    def has_next(self) -> bool:
        return self.line_index < len(self.lines)

    def next(self) -> tuple[int, str]:
        if self.has_next():
            line = self.lines[self.line_index]
            self.line_index += 1
            return line
        else:
            raise LookupError()
