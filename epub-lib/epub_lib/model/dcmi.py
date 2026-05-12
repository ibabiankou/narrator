"""Model definition for Dublin Core Metadata Initiative elements."""
from typing import Optional, Annotated, Dict

from pydantic import StringConstraints, Field
from pydantic_xml import BaseXmlModel, attr

from epub_lib.model import NS_DC, NS_DC_URL, NS_XML, NS_XML_URL

DCMI_NSMAP = {
    NS_DC: NS_DC_URL,
    NS_XML: NS_XML_URL,
}


class BaseDcmiModel(BaseXmlModel, nsmap=DCMI_NSMAP):
    pass


class Identifier(BaseDcmiModel, tag="identifier", ns=NS_DC):
    id: Optional[str] = attr(name="id", default=None)

    unmapped_attributes: Dict[str, str] = Field(exclude=True, default={})

    value: Annotated[str, StringConstraints(strip_whitespace=True)]


class Element(BaseDcmiModel, tag="element", ns=NS_DC):
    """A generalized definition of DCMI elements to be used in EPUB model."""
    id: Optional[str] = attr(name="id", default=None)
    lang: Optional[str] = attr(name="lang", ns=NS_XML, default=None)
    dir: Optional[str] = attr(name="dir", default=None)

    unmapped_attributes: Dict[str, str] = {}

    value: Annotated[Optional[str], StringConstraints(strip_whitespace=True)] = None


class Language(BaseDcmiModel, tag="language", ns=NS_DC):
    id: Optional[str] = attr(name="id", default=None)

    unmapped_attributes: Dict[str, str] = {}

    value: Annotated[str, StringConstraints(strip_whitespace=True)]
