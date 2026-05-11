from epub_lib.model.dcmi import Element, Identifier, Language
from tests.model import assert_no_diff


class TestDcmi:
    def test_write_identifier(self):
        identifier = Identifier(id="pub-id", value="urn:uuid:64593003-b09e-40e7-817a-4a67f0f0c7e2")
        actual_xml_str = identifier.to_xml(exclude_none=True).decode()
        expected_xml_str = """<dc:identifier xmlns:dc="http://purl.org/dc/elements/1.1/" 
                                             id="pub-id">urn:uuid:64593003-b09e-40e7-817a-4a67f0f0c7e2</dc:identifier>"""
        assert_no_diff(actual_xml_str, expected_xml_str)

    def test_parse_identifier(self):
        xml_str = """<dc:identifier xmlns:dc="http://purl.org/dc/elements/1.1/"
                                    random="attribute" 
                                    id="pub-id">urn:uuid:64593003-b09e-40e7-817a-4a67f0f0c7e2</dc:identifier>"""
        actual = Identifier.from_xml(xml_str)
        assert actual.id == "pub-id"
        assert actual.unmapped_attributes.get("random") == "attribute"
        assert actual.value == "urn:uuid:64593003-b09e-40e7-817a-4a67f0f0c7e2"

    def test_write_element(self):
        title = Element(value="My Book Title")
        actual_xml_str = title.to_xml(exclude_none=True).decode()
        expected_xml_str = """<dc:element xmlns:dc="http://purl.org/dc/elements/1.1/">My Book Title</dc:element>"""
        assert_no_diff(actual_xml_str, expected_xml_str)

    def test_parse_element(self):
        xml_str = """<dc:element xmlns:dc="http://purl.org/dc/elements/1.1/">My Book Title</dc:element>"""
        actual = Element.from_xml(xml_str)
        assert actual.value == "My Book Title"

    def test_write_language(self):
        language = Language(value="en-US")
        actual_xml_str = language.to_xml(exclude_none=True).decode()
        expected_xml_str = """<dc:language xmlns:dc="http://purl.org/dc/elements/1.1/">en-US</dc:language>"""
        assert_no_diff(actual_xml_str, expected_xml_str)

    def test_parse_language(self):
        xml_str = """<dc:language xmlns:dc="http://purl.org/dc/elements/1.1/">en-US</dc:language>"""
        actual = Language.from_xml(xml_str)
        assert actual.value == "en-US"
