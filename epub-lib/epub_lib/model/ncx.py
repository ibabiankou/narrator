from typing import List, Optional

from pydantic import ConfigDict
from pydantic_xml import BaseXmlModel, element, attr

from epub_lib.model import NS_XML, NS_NCX_URL, NS_XML_URL, NS_NCX

NCX_NS_MAP = {
    "": NS_NCX_URL,
    NS_XML: NS_XML_URL,
}


class BaseNcxModel(BaseXmlModel, nsmap=NCX_NS_MAP):
    model_config = ConfigDict(
        extra='allow',
    )


class NavLabel(BaseNcxModel, tag="navLabel"):
    text: str = element(name="text")


class Content(BaseNcxModel, tag="content"):
    src: str = attr(name="src")


class NavPoint(BaseNcxModel, tag="navPoint"):
    id: str = attr(name="id")
    play_order: Optional[int] = attr(name="playOrder", default=None)

    nav_label: NavLabel = element(tag="navLabel")
    content: Content = element(tag="content")
    children: List['NavPoint'] = element(tag="navPoint", default=[])


class NavMap(BaseNcxModel, tag="navMap"):
    points: List[NavPoint] = element(tag="navPoint", default=[])


# https://www.daisy.org/z3986/2005/Z3986-2005.html#NCX
class NavigationControl(BaseNcxModel, tag="ncx", search_mode='unordered'):
    version: str = attr()
    lang: str = attr(name="lang", ns=NS_XML)

    nav_map: NavMap = element(tag="navMap")
