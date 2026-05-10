from epub_lib.model.container import Container, RootFile, RootFiles


class TestContainer:
    def test_write_basic_container(self):
        root_file = RootFile(full_path="EPUB/My_Crazy_Life.opf", media_type="application/oebps-package+xml")
        root_files = RootFiles(items=[root_file])
        container = Container(root_files=root_files)
        print("\n", container.to_xml(pretty_print=True).decode())

    def test_basic_container(self):
        xml_str = """<?xml version="1.0"?>
        <container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
           <rootfiles>
              <rootfile
                  full-path="EPUB/My_Crazy_Life.opf"
                  media-type="application/oebps-package+xml" />
           </rootfiles>
        </container>
        """
        actual = Container.from_xml(xml_str)
        assert actual.root_files.items[0].full_path == "EPUB/My_Crazy_Life.opf"
        assert actual.root_files.items[0].media_type == "application/oebps-package+xml"
