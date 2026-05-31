from epub_lib import Epub


class TestEpub:
    def test_file(self):
        epub = Epub("tests/test_data/Swing_Shift_3.epub")
        navigation_control = epub.get_navigation_control()
