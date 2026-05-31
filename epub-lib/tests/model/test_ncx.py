from epub_lib.model.ncx import NavigationControl, NavMap, NavPoint, NavLabel, Content
from tests.model import assert_no_diff


class TestNcx:
    def test_write_ncx(self):
        nav_points = [
            NavPoint(
                id="navPoint-1",
                play_order=1,
                nav_label=NavLabel(text="The Prophet"),
                content=Content(src="Text/cover.xhtml"),
            ),
            NavPoint(
                id="navPoint-2",
                play_order=2,
                nav_label=NavLabel(text="The Coming of the Ship"),
                content=Content(src="Text/chapter-1.xhtml"),
            ),
        ]
        nav_map = NavMap(points=nav_points)
        ncx = NavigationControl(version="2005-1", lang="en", nav_map=nav_map)

        expected_xml_string = """
            <ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1" xml:lang="en">
              <navMap>
                <navPoint id="navPoint-1" playOrder="1">
                  <navLabel>
                    <text>The Prophet</text>
                  </navLabel>
                  <content src="Text/cover.xhtml"/>
                </navPoint>
                <navPoint id="navPoint-2" playOrder="2">
                  <navLabel>
                    <text>The Coming of the Ship</text>
                  </navLabel>
                  <content src="Text/chapter-1.xhtml"/>
                </navPoint>
              </navMap>
            </ncx>
            """
        actual_xml_string = ncx.to_xml(pretty_print=True).decode()
        assert_no_diff(actual_xml_string, expected_xml_string)

    def test_read_ncx(self):
        xml_string = """
            <ncx version="2005-1" xmlns="http://www.daisy.org/z3986/2005/ncx/" xml:lang="en">
              <navMap>
                <navPoint id="navPoint-1" playOrder="1">
                  <navLabel>
                    <text>The Prophet</text>
                  </navLabel>
                  <content src="Text/cover.xhtml"/>
                </navPoint>
                <navPoint id="navPoint-2" playOrder="2">
                  <navLabel>
                    <text>The Coming of the Ship</text>
                  </navLabel>
                  <content src="Text/chapter-1.xhtml"/>
                </navPoint>
              </navMap>
            </ncx>
            """
        actual = NavigationControl.from_xml(xml_string)
        assert actual.version == "2005-1"
        assert actual.lang == "en"
        assert actual.nav_map.points[0].id == "navPoint-1"
        assert actual.nav_map.points[0].play_order == 1
        assert actual.nav_map.points[0].nav_label.text == "The Prophet"
        assert actual.nav_map.points[0].content.src == "Text/cover.xhtml"
        assert actual.nav_map.points[1].id == "navPoint-2"
        assert actual.nav_map.points[1].play_order == 2
        assert actual.nav_map.points[1].nav_label.text == "The Coming of the Ship"
        assert actual.nav_map.points[1].content.src == "Text/chapter-1.xhtml"
