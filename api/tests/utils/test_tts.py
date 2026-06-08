import time

from io import BytesIO
from pathlib import Path

import os

import logging
import pytest
from bs4 import BeautifulSoup
from xmldiff.main import diff_texts

from api.utils.tts import process_xhtml_inplace, tokenize_with_whitespace, process_xhtml_inplace_v2
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

    # @pytest.mark.skip(reason="For manual execution.")
    def test_compare_v1_v2_multiple(self, test_data_loader):
        src_dir_path = os.path.expanduser("~/Downloads/epub/")
        epub_files = list(Path(src_dir_path).rglob("*.epub"))
        epub_files.sort()

        v1_times = []
        v2_times = []
        for epub_path in epub_files[:5]:
            LOG.info("Processing: %s", epub_path)

            file_bytes = BytesIO(epub_path.read_bytes())
            epub = Epub(file_bytes)
            content_files = epub.get_spine_files()
            for content_file in content_files:
                content_bytes = epub._read_file(content_file)

                start = time.perf_counter()
                xml_bytes_v1, fragments_v1, index_v1 = process_xhtml_inplace(content_bytes, 0)
                v1_times.append(time.perf_counter() - start)

                start = time.perf_counter()
                xml_bytes_v2, fragments_v2, index_v2 = process_xhtml_inplace_v2(content_bytes, 0)
                v2_times.append(time.perf_counter() - start)

                assert_no_diff(xml_bytes_v1, xml_bytes_v2)

                assert index_v1 == index_v2

        v1_avg = sum(v1_times)/len(v1_times)
        LOG.info("V1 times avg: %s", v1_avg)
        v2_avg = sum(v2_times)/len(v2_times)
        LOG.info("V2 times avg: %s", v2_avg)
        v2_speedup = ((v1_avg / v2_avg) - 1) * 100
        LOG.info("V2 speedup: %s%%", v2_speedup)
