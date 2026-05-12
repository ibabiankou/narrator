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

    def test_empty_source_metadata_epub2(self):
        xml_str = """<metadata xmlns="http://www.idpf.org/2007/opf" xmlns:dc="http://purl.org/dc/elements/1.1/">
               <meta content="x189.png" name="cover"/>
               <dc:title>Build Your Family Bank</dc:title>
               <dc:source/>
               <dc:relation/>
               <dc:language>en-US</dc:language>
               <dc:identifier id="ISBN9781927958070">9781927958070</dc:identifier>
        </metadata>"""
        Metadata.from_xml(xml_str.encode())

    def test_missing_identifier_metadata_epub2(self):
        xml_str = """<metadata xmlns="http://www.idpf.org/2007/opf" 
                               xmlns:dc="http://purl.org/dc/elements/1.1/" 
                               xmlns:opf="http://www.idpf.org/2007/opf">
                <dc:title>Living Fanon: Global Perspectives</dc:title>
                <dc:creator opf:role="aut">Nigel C. Gibson</dc:creator>
                <dc:source>URN:ISBN:978-0-23011-497-5</dc:source>
                <dc:publisher>Palgrave</dc:publisher>
                <dc:language>en</dc:language>
                <dc:type>Text</dc:type>
                <dc:format>266 pages</dc:format>
                <dc:rights>All rights reserved</dc:rights>
                <meta content="my-cover-image" name="cover"/>
            </metadata>"""
        Metadata.from_xml(xml_str.encode())
