import zipfile

import json
import logging
import os
from io import BytesIO
from pathlib import Path

import pytest

from api.services.epub import EpubService
from epub_lib import Epub

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

    @pytest.mark.skip(reason="For manual execution.")
    def test_inline_fragments(self):
        src_dir_path = os.path.expanduser("~/Downloads/epub/")
        dest_dir_path = Path(os.path.expanduser("~/repos/narrator/out/fragments/"))
        epub_files = list(Path(src_dir_path).rglob("*.epub"))
        epub_files.sort()

        for epub_path in epub_files:
            LOG.info("Processing: %s", epub_path)

            file_bytes = BytesIO(epub_path.read_bytes())
            clean_epub = svc.remove_links(file_bytes)
            epub_with_fragments, fragments = svc.inline_fragments(clean_epub)

            epub_file_name = dest_dir_path.joinpath(epub_path.stem + "_updated.epub")
            with open(epub_file_name, "wb") as f:
                f.write(epub_with_fragments.getvalue())

            fragments_file_name = dest_dir_path.joinpath(epub_path.stem + "_fragments.json")
            with open(fragments_file_name, "w") as f:
                json.dump({k: v.model_dump() for k, v in fragments.items()}, f, indent=2)

            epub_extracted_path = dest_dir_path.joinpath(epub_path.stem + "_unpacked")
            zipfile.ZipFile(epub_with_fragments).extractall(path=epub_extracted_path)

    def test_something(self, test_data_loader):
        """A content file with multiple navigation items. Second nav item has a pause fragment that was breaking
        narration manifest generation due to the missing visited_ids."""
        epub_bytes = test_data_loader("Antecedents_Assembly.epub", text=False)
        dest_dir_path = Path(os.path.expanduser("~/repos/narrator/out/fragments/"))

        epub = Epub(epub_bytes)

        clean_epub = svc.remove_links(epub_bytes)
        epub_with_fragments, fragments = svc.inline_fragments(clean_epub)

        epub_file_name = dest_dir_path.joinpath("Antecedents_Assembly" + "_updated.epub")
        with open(epub_file_name, "wb") as f:
            f.write(epub_with_fragments.getvalue())

        fragments_file_name = dest_dir_path.joinpath("Antecedents_Assembly" + "_fragments.json")
        with open(fragments_file_name, "w") as f:
            json.dump({k: v.model_dump() for k, v in fragments.items()}, f, indent=2)

        epub_extracted_path = dest_dir_path.joinpath("Antecedents_Assembly" + "_unpacked")
        zipfile.ZipFile(epub_with_fragments).extractall(path=epub_extracted_path)

        publication_content = epub.get_publication_content()
        narration_manifest = svc.build_narration_manifest(publication_content, fragments)

    @pytest.mark.skip(reason="For manual execution.")
    def test_manifest(self):
        src_dir_path = os.path.expanduser("~/Downloads/epub/")
        dest_dir_path = Path(os.path.expanduser("~/repos/narrator/out/manifest/"))
        epub_files = list(Path(src_dir_path).rglob("*.epub"))
        epub_files.sort()

        for epub_path in epub_files:
            LOG.info("Processing: %s", epub_path)

            file_bytes = BytesIO(epub_path.read_bytes())
            clean_epub = svc.remove_links(file_bytes)

            epub_with_fragments, fragments = svc.inline_fragments(clean_epub)
            epub_file_name = dest_dir_path.joinpath(epub_path.stem + "_updated.epub")
            with open(epub_file_name, "wb") as f:
                f.write(epub_with_fragments.getvalue())
            fragments_file_name = dest_dir_path.joinpath(epub_path.stem + "_fragments.json")
            with open(fragments_file_name, "w") as f:
                json.dump({k: v.model_dump() for k, v in fragments.items()}, f, indent=2)

            epub = Epub(epub_with_fragments)
            publication_content = epub.get_publication_content()
            publication_content_file_name = dest_dir_path.joinpath(epub_path.stem + "_publication_content.json")
            with open(publication_content_file_name, "w") as f:
                f.write(publication_content.model_dump_json(indent=2))

            narration_manifest = svc.build_narration_manifest(publication_content, fragments)
            narration_manifest_file_name = dest_dir_path.joinpath(epub_path.stem + "_narration_manifest.json")
            with open(narration_manifest_file_name, "w") as f:
                f.write(narration_manifest.model_dump_json(indent=2))

    def test_successful_narration_manifest_creation(self, test_data_loader):
        file_name = "empire-rising-6.epub"
        file_name_no_ext = file_name.split(".")[0]
        epub_bytes = test_data_loader(file_name, text=False)
        dest_dir_path = Path(os.path.expanduser("~/repos/narrator/out/fragments/"))

        epub = Epub(epub_bytes)

        clean_epub = svc.remove_links(epub_bytes)
        epub_with_fragments, fragments = svc.inline_fragments(clean_epub)

        epub_file_name = dest_dir_path.joinpath(file_name_no_ext + "_updated.epub")
        with open(epub_file_name, "wb") as f:
            f.write(epub_with_fragments.getvalue())

        fragments_file_name = dest_dir_path.joinpath(file_name_no_ext + "_fragments.json")
        with open(fragments_file_name, "w") as f:
            json.dump({k: v.model_dump() for k, v in fragments.items()}, f, indent=2)

        epub_extracted_path = dest_dir_path.joinpath(file_name_no_ext + "_unpacked")
        zipfile.ZipFile(epub_with_fragments).extractall(path=epub_extracted_path)

        publication_content = epub.get_publication_content()
        narration_manifest = svc.build_narration_manifest(publication_content, fragments)
