import os
from pathlib import Path

import pytest

from epub_lib import Epub


class TestEpub:
    def test_epub3_navigation(self):
        epub = Epub("tests/test_data/Swing_Shift_3.epub")
        navigation_control = epub._get_navigation_control()
        assert navigation_control is not None
        assert len(navigation_control.nav_map.points) == 41

    def test_epub2_navigation(self):
        epub = Epub("tests/test_data/Dungeon_Crawler_Carl.epub")
        toc = epub._get_table_of_content()
        assert toc is not None
        assert len(toc.items) == 60

    def test_toc(self):
        epub = Epub("tests/test_data/Dungeon_Crawler_Carl.epub")
        toc = epub.get_table_of_content()
        unique_spine_refs = set([i.idref for i in epub.package.spine.items])
        assert len(toc.items) == len(unique_spine_refs)

    @pytest.mark.skip(reason="For manual execution only.")
    def test_toc_all_files(self):
        dir_path = os.path.expanduser("~/Downloads/epub")
        epub_files = list(Path(dir_path).rglob("*.epub"))
        for epub_path in epub_files:
            try:
                epub = Epub(str(epub_path))
                toc = epub.get_table_of_content()
                assert toc is not None
                print(f"Successfully processed: {epub_path.name}")
                print(toc.model_dump_json(indent=2))
            except Exception as e:
                print(f"Failed to process {epub_path.name}: {e}")
