from epub_lib import Epub


class TestEpub:
    def test_epub3_navigation(self):
        epub = Epub("tests/test_data/Swing_Shift_3.epub")
        navigation_control = epub.get_navigation_control()
        assert navigation_control is not None
        assert len(navigation_control.nav_map.points) == 41

    def test_epub2_navigation(self):
        epub = Epub("tests/test_data/Dungeon_Crawler_Carl.epub")
        toc = epub.get_table_of_content()
        assert toc is not None
        assert len(toc.items) == 60
