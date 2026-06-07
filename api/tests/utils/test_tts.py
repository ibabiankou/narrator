import logging

from api.utils.tts import process_xhtml_inplace

LOG = logging.getLogger(__name__)


class TestTts:
    def test_first(self):
        html_str = "<p>This is a test</p>"

        output_html_bytes, frags, last_id = process_xhtml_inplace(html_str.encode(), 0)
        LOG.info(output_html_bytes.decode())
        LOG.info(frags.model_dump_json(indent=2))

    def test_short_no_punct(self, test_data_loader):
        html_str = test_data_loader("short_no_punct.html")
        output_html_bytes, frags, last_id = process_xhtml_inplace(html_str.encode(), 0)

    def test_3(self, test_data_loader):
        html_str = test_data_loader("3.html")
        output_html_bytes, frags, last_id = process_xhtml_inplace(html_str.encode(), 0)
