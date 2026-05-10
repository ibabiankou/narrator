from xmldiff.main import diff_texts

from epub_lib.model.package import Meta, Identifier, Title, Language, Metadata, Item, Manifest, Spine, ItemRef, Link, \
    Collection, Package


# noinspection PyTypeChecker
def assert_no_diff(left, right):
    assert len(diff_texts(left, right)) == 0


class TestPackage:
    def test_write_meta(self):
        meta = Meta(property="dcterms:modified", value="2011-01-01T12:00:00Z")
        actual_xml_str = meta.to_xml(exclude_none=True).decode()

        expected_xml_str = """<meta xmlns="http://www.idpf.org/2007/opf" 
                                    xmlns:opf="http://www.idpf.org/2007/opf" 
                                    xmlns:dc="http://purl.org/dc/elements/1.1/" 
                                    xmlns:xsi="http://purl.org/dc/elements/1.1/" 
                                    property="dcterms:modified">2011-01-01T12:00:00Z</meta>"""
        assert_no_diff(actual_xml_str, expected_xml_str)

    def test_parse_meta(self):
        xml_str = """<meta xmlns="http://www.idpf.org/2007/opf" 
                           property="dcterms:modified">2011-01-01T12:00:00Z</meta>"""
        actual = Meta.from_xml(xml_str)
        assert actual.property == "dcterms:modified"
        assert actual.value == "2011-01-01T12:00:00Z"

    def test_parse_meta_coverimage(self):
        xml_str = """<meta xmlns="http://www.idpf.org/2007/opf" content="coverimage" name="cover"/>"""
        actual = Meta.from_xml(xml_str)
        assert actual.content == "coverimage"
        assert actual.name == "cover"

    def test_write_identifier(self):
        identifier = Identifier(id="pub-id", value="urn:uuid:64593003-b09e-40e7-817a-4a67f0f0c7e2")
        actual_xml_str = identifier.to_xml(exclude_none=True).decode()
        expected_xml_str = """<dc:identifier xmlns="http://www.idpf.org/2007/opf" 
                                             xmlns:opf="http://www.idpf.org/2007/opf" 
                                             xmlns:dc="http://purl.org/dc/elements/1.1/" 
                                             xmlns:xsi="http://purl.org/dc/elements/1.1/"
                                             id="pub-id">urn:uuid:64593003-b09e-40e7-817a-4a67f0f0c7e2</dc:identifier>"""
        assert_no_diff(actual_xml_str, expected_xml_str)

    def test_parse_identifier(self):
        xml_str = """<dc:identifier xmlns:dc="http://purl.org/dc/elements/1.1/" 
                                    id="pub-id">urn:uuid:64593003-b09e-40e7-817a-4a67f0f0c7e2</dc:identifier>"""
        actual = Identifier.from_xml(xml_str)
        assert actual.id == "pub-id"
        assert actual.value == "urn:uuid:64593003-b09e-40e7-817a-4a67f0f0c7e2"

    def test_write_title(self):
        title = Title(value="My Book Title")
        actual_xml_str = title.to_xml(exclude_none=True).decode()
        expected_xml_str = """<dc:title xmlns="http://www.idpf.org/2007/opf" 
                                 xmlns:opf="http://www.idpf.org/2007/opf" 
                                 xmlns:dc="http://purl.org/dc/elements/1.1/" 
                                 xmlns:xsi="http://purl.org/dc/elements/1.1/">My Book Title</dc:title>"""
        assert_no_diff(actual_xml_str, expected_xml_str)

    def test_parse_title(self):
        xml_str = """<dc:title xmlns:dc="http://purl.org/dc/elements/1.1/">My Book Title</dc:title>"""
        actual = Title.from_xml(xml_str)
        assert actual.value == "My Book Title"

    def test_write_language(self):
        language = Language(value="en-US")
        actual_xml_str = language.to_xml(exclude_none=True).decode()
        expected_xml_str = """<dc:language xmlns="http://www.idpf.org/2007/opf" 
                                 xmlns:opf="http://www.idpf.org/2007/opf" 
                                 xmlns:dc="http://purl.org/dc/elements/1.1/" 
                                 xmlns:xsi="http://purl.org/dc/elements/1.1/">en-US</dc:language>"""
        assert_no_diff(actual_xml_str, expected_xml_str)

    def test_parse_language(self):
        xml_str = """<dc:language xmlns:dc="http://purl.org/dc/elements/1.1/">en-US</dc:language>"""
        actual = Language.from_xml(xml_str)
        assert actual.value == "en-US"

    def test_write_link(self):
        link = Link(href="link.html", rel="item", media_type="application/xhtml+xml")
        actual_xml_str = link.to_xml(exclude_none=True).decode()
        expected_xml_str = """<link xmlns="http://www.idpf.org/2007/opf" 
                                    xmlns:opf="http://www.idpf.org/2007/opf" 
                                    xmlns:dc="http://purl.org/dc/elements/1.1/" 
                                    xmlns:xsi="http://purl.org/dc/elements/1.1/"
                                    media-type="application/xhtml+xml" rel="item" href="link.html"/>"""
        assert_no_diff(actual_xml_str, expected_xml_str)

    def test_parse_link(self):
        xml_str = """<link xmlns="http://www.idpf.org/2007/opf" href="link.html" rel="item" media-type="application/xhtml+xml"/>"""
        actual = Link.from_xml(xml_str)
        assert actual.href == "link.html"
        assert actual.rel == "item"
        assert actual.media_type == "application/xhtml+xml"

    def test_write_metadata(self):
        identifier = Identifier(id="pub-id", value="id-val")
        title = Title(value="title-val")
        language = Language(value="lang-val")
        meta = Meta(property="meta-prop", value="meta-val")
        metadata = Metadata(identifier=[identifier], title=[title], language=[language], meta=[meta])
        actual_xml_str = metadata.to_xml(exclude_none=True).decode()

        expected_xml_str = """<metadata xmlns="http://www.idpf.org/2007/opf" 
                                 xmlns:opf="http://www.idpf.org/2007/opf" 
                                 xmlns:dc="http://purl.org/dc/elements/1.1/" 
                                 xmlns:xsi="http://purl.org/dc/elements/1.1/">
                                <dc:identifier id="pub-id">id-val</dc:identifier>
                                <dc:title>title-val</dc:title>
                                <dc:language>lang-val</dc:language>
                                <meta property="meta-prop">meta-val</meta>
                              </metadata>"""
        assert_no_diff(actual_xml_str, expected_xml_str)

    def test_parse_metadata(self):
        xml_str = """<metadata xmlns="http://www.idpf.org/2007/opf" xmlns:dc="http://purl.org/dc/elements/1.1/">
                       <dc:identifier id="pub-id">id-val</dc:identifier>
                       <dc:title>title-val</dc:title>
                       <dc:language>lang-val</dc:language>
                       <meta property="meta-prop">meta-val</meta>
                     </metadata>"""
        actual = Metadata.from_xml(xml_str)
        assert actual.identifier[0].id == "pub-id"
        assert actual.identifier[0].value == "id-val"
        assert actual.title[0].value == "title-val"
        assert actual.language[0].value == "lang-val"
        assert actual.meta[0].property == "meta-prop"
        assert actual.meta[0].value == "meta-val"

    def test_write_item(self):
        item = Item(id="item-id", href="item.html", media_type="application/xhtml+xml")
        actual_xml_str = item.to_xml(exclude_none=True).decode()
        expected_xml_str = """<item xmlns="http://www.idpf.org/2007/opf"
                                    xmlns:opf="http://www.idpf.org/2007/opf" 
                                    xmlns:dc="http://purl.org/dc/elements/1.1/" 
                                    xmlns:xsi="http://purl.org/dc/elements/1.1/"  
                                    id="item-id" href="item.html" media-type="application/xhtml+xml"/>"""
        assert_no_diff(actual_xml_str, expected_xml_str)

    def test_parse_item(self):
        xml_str = """<item xmlns="http://www.idpf.org/2007/opf" id="item-id" href="item.html" media-type="application/xhtml+xml"/>"""
        actual = Item.from_xml(xml_str)
        assert actual.id == "item-id"
        assert actual.href == "item.html"
        assert actual.media_type == "application/xhtml+xml"

    def test_write_manifest(self):
        item1 = Item(id="item1", href="item1.html", media_type="application/xhtml+xml")
        item2 = Item(id="item2", href="item2.html", media_type="application/xhtml+xml")
        manifest = Manifest(item=[item1, item2])
        actual_xml_str = manifest.to_xml(exclude_none=True).decode()
        expected_xml_str = """<manifest xmlns="http://www.idpf.org/2007/opf"
                                       xmlns:opf="http://www.idpf.org/2007/opf" 
                                       xmlns:dc="http://purl.org/dc/elements/1.1/" 
                                       xmlns:xsi="http://purl.org/dc/elements/1.1/">
                              <item id="item1" href="item1.html" media-type="application/xhtml+xml"/>
                              <item id="item2" href="item2.html" media-type="application/xhtml+xml"/>
                            </manifest>"""
        assert_no_diff(actual_xml_str, expected_xml_str)

    def test_parse_manifest(self):
        xml_str = """<manifest xmlns="http://www.idpf.org/2007/opf">
                        <item id="item1" href="item1.html" media-type="application/xhtml+xml"/>
                        <item id="item2" href="item2.html" media-type="application/xhtml+xml"/>
                     </manifest>"""
        actual = Manifest.from_xml(xml_str)
        assert len(actual.item) == 2
        assert actual.item[0].id == "item1"
        assert actual.item[0].href == "item1.html"
        assert actual.item[0].media_type == "application/xhtml+xml"

    def test_write_itemref(self):
        itemref = ItemRef(idref="item-id", linear="yes")
        actual_xml_str = itemref.to_xml(exclude_none=True).decode()
        expected_xml_str = """<itemref xmlns="http://www.idpf.org/2007/opf"
                                       xmlns:opf="http://www.idpf.org/2007/opf" 
                                       xmlns:dc="http://purl.org/dc/elements/1.1/" 
                                       xmlns:xsi="http://purl.org/dc/elements/1.1/"
                                       linear="yes" idref="item-id"/>"""
        assert_no_diff(actual_xml_str, expected_xml_str)

    def test_parse_itemref(self):
        xml_str = """<itemref xmlns="http://www.idpf.org/2007/opf" idref="item-id" linear="yes"/>"""
        actual = ItemRef.from_xml(xml_str)
        assert actual.idref == "item-id"
        assert actual.linear == "yes"

    def test_write_spine(self):
        spine = Spine(toc="ncx", items=[ItemRef(idref="item1"), ItemRef(idref="item2")])
        actual_xml_str = spine.to_xml(exclude_none=True).decode()
        expected_xml_str = """<spine xmlns="http://www.idpf.org/2007/opf"
                                     xmlns:opf="http://www.idpf.org/2007/opf" 
                                     xmlns:dc="http://purl.org/dc/elements/1.1/" 
                                     xmlns:xsi="http://purl.org/dc/elements/1.1/"
                                     toc="ncx"><itemref idref="item1"/><itemref idref="item2"/></spine>"""
        assert_no_diff(actual_xml_str, expected_xml_str)

    def test_parse_spine(self):
        xml_str = """<spine xmlns="http://www.idpf.org/2007/opf" toc="ncx"><itemref idref="item1"/><itemref idref="item2"/></spine>"""
        actual = Spine.from_xml(xml_str)
        assert actual.toc == "ncx"
        assert len(actual.items) == 2
        assert actual.items[0].idref == "item1"
        assert actual.items[1].idref == "item2"

    def test_write_collection(self):
        collection = Collection(
            role="mo-assets",
            links=[
                Link(href="item1.html", rel="item", media_type="application/xhtml+xml"),
                Link(href="item2.html", rel="item", media_type="application/xhtml+xml"),
            ],
        )
        actual_xml_str = collection.to_xml(exclude_none=True).decode()
        expected_xml_str = """<collection
                                             xmlns="http://www.idpf.org/2007/opf"
                                             xmlns:opf="http://www.idpf.org/2007/opf" 
                                             xmlns:dc="http://purl.org/dc/elements/1.1/" 
                                             xmlns:xsi="http://purl.org/dc/elements/1.1/"
                                             role="mo-assets">
                                        <link media-type="application/xhtml+xml" rel="item" href="item1.html"/>
                                        <link media-type="application/xhtml+xml" rel="item" href="item2.html"/>
                                    </collection>"""
        assert_no_diff(actual_xml_str, expected_xml_str)

    def test_parse_collection(self):
        xml_str = """<collection xmlns="http://www.idpf.org/2007/opf" id="c1" role="mo-assets">
                        <link href="item1.html" rel="item" media-type="application/xhtml+xml"/>
                        <link href="item2.html" rel="item" media-type="application/xhtml+xml"/>
                     </collection>"""
        actual = Collection.from_xml(xml_str)
        assert actual.id == "c1"
        assert actual.role == "mo-assets"
        assert len(actual.links) == 2
        assert actual.links[0].href == "item1.html"
        assert actual.links[1].href == "item2.html"

    def test_minimal_package(self):
        xml_str = """<package
                             xmlns="http://www.idpf.org/2007/opf" 
                             xmlns:dc="http://purl.org/dc/elements/1.1/" 
                             xmlns:opf="http://www.idpf.org/2007/opf" 
                             xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"  
                             unique-identifier="pub-id" 
                             version="3.0">
                <metadata>
                   <dc:identifier id="pub-id">urn:uuid:A1B0D67E-2E81-4DF5-9E67-A64CBE366809</dc:identifier>
                   <dc:title>Norwegian Wood</dc:title>
                   <dc:language>en</dc:language>
                   <meta property="dcterms:modified">2011-01-01T12:00:00Z</meta>
                </metadata>
                <manifest>
                   <item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>
                </manifest>
                <spine toc="ncx">
                   <itemref idref="ncx"/>
                </spine>
            </package>"""
        Package.from_xml(xml_str)
