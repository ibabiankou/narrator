from epub_lib.model.package import Metadata


class TestRealCases:
    def test_can_parse_metadata_epub2(self):
        xml_str = """<metadata xmlns="http://www.idpf.org/2007/opf" xmlns:dc="http://purl.org/dc/elements/1.1/">
               <dc:title>Drawing Down the Spirits</dc:title>
               <dc:creator>Kenaz Filan</dc:creator>
               <dc:date>2010-10-20</dc:date>
               <dc:identifier id="p9781594779282">9781594779282</dc:identifier>
               <dc:type>Text</dc:type>
               <dc:language>en</dc:language>
               <dc:rights>All Rights Reserved</dc:rights>
               <dc:publisher>Inner Traditions / Bear &amp; Company</dc:publisher>
        </metadata>"""
        Metadata.from_xml(xml_str.encode())
