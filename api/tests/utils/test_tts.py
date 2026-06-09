from pathlib import Path

import logging
import os
import pytest
import shutil
from bs4 import BeautifulSoup
from io import BytesIO
from xmldiff.main import diff_texts

from api.utils.tts import process_xhtml_inplace, tokenize_with_whitespace, process_xhtml_inplace_v2, BLOCK_TAGS, \
    tokenize_tag_content
from epub_lib import Epub

LOG = logging.getLogger(__name__)


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


class TestTts:
    def test_first(self):
        html_str = "<p>This is a test</p>"

        output_html_bytes, frags, last_id = process_xhtml_inplace(html_str.encode(), 0)

    def test_short_no_punct(self, test_data_loader):
        html_str = test_data_loader("short_no_punct.html")
        output_html_bytes, frags, last_id = process_xhtml_inplace(html_str.encode(), 0)

    def test_3(self, test_data_loader):
        html_str = test_data_loader("3.html")
        output_html_bytes, frags, last_id = process_xhtml_inplace(html_str.encode(), 0)

    def test_tokenize_with_whitespace_specific(self, test_data_loader):
        cases = [" ", "\n", "\t", "\r", " word", "word ", " word "]
        for text in cases:
            tokens = tokenize_with_whitespace(text)
            reconstructed = "".join(tokens)
            assert len(tokens) > 0
            assert text == reconstructed

    def test_tokenize_with_whitespace(self, test_data_loader):
        files = ["short_no_punct.html", "3.html"]
        for file in files:
            html_str = test_data_loader(file)
            soup = BeautifulSoup(html_str, 'xml')
            full_text = soup.find("body").get_text()
            tokens = tokenize_with_whitespace(full_text)
            reconstructed = "".join(tokens)

            assert len(full_text) > 0
            assert full_text == reconstructed

    def test_compare_v1_v2(self, test_data_loader):
        files = ["short_no_punct.html", "3.html"]
        for file in files:
            html_str = test_data_loader(file)

            xml_bytes_v1, fragments_v1, index_v1 = process_xhtml_inplace(html_str.encode(), 0)
            xml_bytes_v2, fragments_v2, index_v2 = process_xhtml_inplace_v2(html_str.encode(), 0)

            assert_no_diff(xml_bytes_v1, xml_bytes_v2)

            assert index_v1 == index_v2

    @pytest.mark.skip(reason="For manual execution.")
    def test_tokenize_tag_content_real_books(self, test_data_loader):
        src_dir_path = os.path.expanduser("~/Downloads/epub/")
        epub_files = list(Path(src_dir_path).rglob("*.epub"))
        dest_dir_path = Path(os.path.expanduser("~/repos/narrator/out/tests/"))
        epub_files.sort()

        for epub_path in epub_files:
            LOG.info("Processing EPUB: %s", epub_path)

            file_bytes = BytesIO(epub_path.read_bytes())
            epub = Epub(file_bytes)
            content_files = epub.get_spine_files()
            for content_file in content_files:
                content_bytes = epub._read_file(content_file)

                soup = BeautifulSoup(content_bytes, 'xml')

                for tag in soup.find_all():
                    # Only work with leaf block nodes.
                    if tag.name not in BLOCK_TAGS: continue
                    if tag.find(BLOCK_TAGS): continue

                    raw_text = tag.get_text().strip()
                    tokens = tokenize_tag_content(tag)
                    token_text = "".join([t.raw_text for t in tokens]).strip()

                    if raw_text != token_text:
                        LOG.error("Failed on file %s", content_file)

                        epub_extracted_path = dest_dir_path / "unpacked_epub"
                        shutil.rmtree(epub_extracted_path, ignore_errors=True)
                        epub.zip_file.extractall(path=epub_extracted_path)

                        assert False, f"Raw text mismatch: '{raw_text}' != '{token_text}'"
