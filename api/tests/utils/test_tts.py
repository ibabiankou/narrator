import re
from pathlib import Path

import logging
import os
import pytest
import shutil
from bs4 import BeautifulSoup, Tag
from io import BytesIO
from xmldiff.main import diff_texts

from api.utils.tts import tokenize_with_whitespace, split_tokens_into_fragments, FragmentInjector, \
    process_xhtml_inplace, tokenize_tag_content
from common_lib.models.tts import Token, FragmentListBuilder
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
    def test_scene_break_detection(self):
        cases = [
            ([Token("---")], True),
            ([Token("___")], True),
            ([Token("***")], True),
            ([Token("!")], True),
            ([Token("◆◆◆")], True),
            ([Token("")], False),
            ([Token(" ")], False),
            ([Token("aaa")], False),
            ([Token("888")], False),
        ]
        for case in cases:
            assert FragmentInjector._scene_break(case[0]) == case[1]

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

    @pytest.mark.skip(reason="For manual execution.")
    def test_process_xhtml_inplace_v2_real_books(self, test_data_loader):
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

                try:
                    process_xhtml_inplace(content_bytes, 0)
                except:
                    LOG.error("Failed on file %s", content_file)

                    epub_extracted_path = dest_dir_path / "unpacked_epub"
                    shutil.rmtree(epub_extracted_path, ignore_errors=True)
                    epub.zip_file.extractall(path=epub_extracted_path)

                    assert False

    def test_split_tokens_into_fragments_one_empty_token(self):
        words = [" "]
        tokens = [Token(word) for word in words]
        fragments = split_tokens_into_fragments(tokens)

        assert len(fragments) == 1

    def test_split_tokens_into_fragments_no_split(self):
        words = ["Hell ", "my", "friend!"]
        tokens = [Token(word) for word in words]
        fragments = split_tokens_into_fragments(tokens, 7)

        assert len(fragments) == 1, "Should not split tokens without whitespace in between."

    def test_fragment_injector_text_only(self, test_data_loader):
        html_str = test_data_loader("fragment_injector.html")
        soup = BeautifulSoup(html_str, 'xml')

        # noinspection PyTypeChecker
        tag: Tag = soup.find(attrs={"id": "text-only"})
        assert tag is not None

        fb = FragmentListBuilder()
        fi = FragmentInjector(tag, fb, set(), target_length=20)
        fi.inject()

        expected_html = """
        <p id="text-only"><span class="nf" id="n-0">The idea helps explain </span><span class="nf" id="n-1">why free markets.</span></p>
        """
        assert expected_html.strip() == str(tag)

    def test_fragment_injector_has_tag(self, test_data_loader):
        html_str = test_data_loader("fragment_injector.html")
        soup = BeautifulSoup(html_str, 'xml')

        # noinspection PyTypeChecker
        tag: Tag = soup.find(attrs={"id": "with-tag"})
        assert tag is not None

        fb = FragmentListBuilder()
        fi = FragmentInjector(tag, fb, set(), target_length=20)
        fi.inject()

        expected_html = """
        <p id="with-tag"><span class="nf" id="n-0">The <b>idea</b> helps explain </span><span class="nf" id="n-1">why free markets.</span></p>
        """
        assert expected_html.strip() == str(tag)

    def test_fragment_injector_mid_tag(self, test_data_loader):
        html_str = test_data_loader("fragment_injector.html")
        soup = BeautifulSoup(html_str, 'xml')

        # noinspection PyTypeChecker
        tag: Tag = soup.find(attrs={"id": "mid-tag"})
        assert tag is not None

        fb = FragmentListBuilder()
        fi = FragmentInjector(tag, fb, set(), target_length=20)
        fi.inject()

        expected_html = """
        <p id="mid-tag"><span class="nf" id="n-0">The <b>idea helps explain </b></span><span class="nf" id="n-1"><b>why free</b> markets.</span></p>
        """
        assert expected_html.strip() == str(tag)

    def test_fragment_injector_end_tag(self, test_data_loader):
        html_str = test_data_loader("fragment_injector.html")
        soup = BeautifulSoup(html_str, 'xml')

        # noinspection PyTypeChecker
        tag: Tag = soup.find(attrs={"id": "end-tag"})
        assert tag is not None

        fb = FragmentListBuilder()
        fi = FragmentInjector(tag, fb, set(), target_length=20)
        fi.inject()

        expected_html = """
        <p id="end-tag"><span class="nf" id="n-0">The <b>idea helps explain </b></span><span class="nf" id="n-1">why free markets.</span></p>
        """
        assert expected_html.strip() == str(tag)

    def test_fragment_injector_start_tag(self, test_data_loader):
        html_str = test_data_loader("fragment_injector.html")
        soup = BeautifulSoup(html_str, 'xml')

        # noinspection PyTypeChecker
        tag: Tag = soup.find(attrs={"id": "start-tag"})
        assert tag is not None

        fb = FragmentListBuilder()
        fi = FragmentInjector(tag, fb, set(), target_length=20)
        fi.inject()

        expected_html = """
        <p id="start-tag"><span class="nf" id="n-0">The idea helps explain </span><span class="nf" id="n-1"><b>why free </b>markets.</span></p>
        """
        assert expected_html.strip() == str(tag)

    def test_tokenize_tag_content_punct_on_br(self, test_data_loader):
        html_str = test_data_loader("fragment_injector.html")
        soup = BeautifulSoup(html_str, 'xml')

        # noinspection PyTypeChecker
        tag: Tag = soup.find(attrs={"id": "line-br"})
        assert tag is not None

        tokens = tokenize_tag_content(tag)
        for t in tokens:
            if t.raw_text == "explain":
                assert t.add_punctuation_in_tts
                return

        assert False, "Token not found."

    @pytest.mark.skip(reason="For manual execution.")
    def test_check_for_unexpected_characters(self, test_data_loader):
        src_dir_path = os.path.expanduser("~/Downloads/epub/")
        epub_files = list(Path(src_dir_path).rglob("*.epub"))
        dest_dir_path = Path(os.path.expanduser("~/repos/narrator/out/tests/"))
        epub_files.sort()

        not_allowed = re.compile(r"[^a-zA-Z0-9\s.…,?!;:'\"\-=+%()\[\]{}$/&*#@©~]")

        for epub_path in epub_files:
            LOG.info("Processing EPUB: %s", epub_path)

            file_bytes = BytesIO(epub_path.read_bytes())
            epub = Epub(file_bytes)
            content_files = epub.get_spine_files()
            for content_file in content_files:
                content_bytes = epub._read_file(content_file)

                try:
                    content_bytes, fragments, frag_id = process_xhtml_inplace(content_bytes, 0)
                    text = " ".join([f.text for f in fragments.root if f.type == "text"])
                    unexpected_characters = set(not_allowed.findall(text))
                    if unexpected_characters:
                        LOG.error("Unexpected characters in file %s: %s", content_file, unexpected_characters)
                except:
                    LOG.error("Failed on file %s", content_file)

                    epub_extracted_path = dest_dir_path / "unpacked_epub"
                    shutil.rmtree(epub_extracted_path, ignore_errors=True)
                    epub.zip_file.extractall(path=epub_extracted_path)

                    assert False
