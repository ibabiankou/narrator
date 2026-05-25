"""Model definition for Dublin Core Metadata Initiative elements."""
import logging
from typing import Optional, Annotated, Dict

import langcodes
from pydantic import StringConstraints, Field
from pydantic_xml import BaseXmlModel, attr

from epub_lib.model import NS_DC, NS_DC_URL, NS_XML, NS_XML_URL

DCMI_NSMAP = {
    NS_DC: NS_DC_URL,
    NS_XML: NS_XML_URL,
}

LOG = logging.getLogger(__name__)

class BaseDcmiModel(BaseXmlModel, nsmap=DCMI_NSMAP):
    pass


class Identifier(BaseDcmiModel, tag="identifier", ns=NS_DC):
    id: Optional[str] = attr(name="id", default=None)

    unmapped_attributes: Dict[str, str] = Field(exclude=True, default={})

    value: Annotated[Optional[str], StringConstraints(strip_whitespace=True)] = None


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

    value: Annotated[Optional[str], StringConstraints(strip_whitespace=True)] = None

    def is_english(self):
        if self.value is None:
            LOG.warning("Empty language tag.")
            return False

        try:
            # Validates and parses the RFC 5646 tag
            tag = langcodes.Language.get(self.value)
            return tag.language == 'en'
        except (ValueError, TypeError):
            # Raised if the string is not a well-formed RFC 5646 tag
            LOG.warning("Invalid language tag: %s", self.value)
            return False
