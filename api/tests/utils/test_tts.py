import logging
from bs4 import BeautifulSoup

from api.utils.tts import process_xhtml_inplace, tokenize_with_whitespace

LOG = logging.getLogger(__name__)


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
