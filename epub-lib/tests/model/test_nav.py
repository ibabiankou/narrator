from pathlib import Path

from epub_lib.model.nav import PublicationContentBuilder
from epub_lib.model.package import Item


class TestNav:
    def test_publication_with_root_dir(self):
        base_dir_path = Path("ops/9781623651824.opf").parent
        builder = PublicationContentBuilder(base_dir_path)
        item = Item(href="html/content.xhtml", id="id", media_type="application/xhtml+xml")
        builder.add_manifest_item(item)

        content = builder.build()
        assert content.spine_items[0].href == "ops/html/content.xhtml"

    def test_publication_without_root_dir(self):
        base_dir_path = Path("9781623651824.opf").parent
        builder = PublicationContentBuilder(base_dir_path)
        item = Item(href="html/content.xhtml", id="id", media_type="application/xhtml+xml")
        builder.add_manifest_item(item)

        content = builder.build()
        assert content.spine_items[0].href == "html/content.xhtml"
