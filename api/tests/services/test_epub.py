import logging
import os
from io import BytesIO
from pathlib import Path

import pytest

from api.services.epub import EpubService

LOG = logging.getLogger(__name__)

svc = EpubService()


class TestEpubService:

    @pytest.mark.skip(reason="For manual execution.")
    def test_remove_links(self):
        src_dir_path = os.path.expanduser("~/Downloads/epub/")
        dest_dir_path = Path(os.path.expanduser("~/repos/narrator/out/clean_epub/"))
        epub_files = list(Path(src_dir_path).rglob("*.epub"))

        for epub_path in epub_files:
            LOG.info("Processing: %s", epub_path)

            file_bytes = BytesIO(epub_path.read_bytes())

            clean_epub = svc.remove_links(file_bytes)

            file_name = dest_dir_path.joinpath(epub_path.stem + "_clean.epub")
            with open(file_name, "wb") as f:
                f.write(clean_epub.getvalue())
