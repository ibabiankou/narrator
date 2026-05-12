"""Model definition for Open Packaging Format."""
from typing import List, Optional, Annotated

from pydantic import StringConstraints
from pydantic_xml import BaseXmlModel, element, attr

from epub_lib.model import NS_OPF_URL, NS_OPF, NS_DC, NS_DC_URL, NS_XSI, NS_XSI_URL, NS_XML, NS_XML_URL
from epub_lib.model.dcmi import Identifier, Element, Language

PACKAGE_NS_MAP = {
    "": NS_OPF_URL,
    NS_OPF: NS_OPF_URL,
    NS_DC: NS_DC_URL,
    NS_XSI: NS_XSI_URL,
    NS_XML: NS_XML_URL,
}

class BasePackageModel(BaseXmlModel, nsmap=PACKAGE_NS_MAP):
    pass


# This is a combination of EPUB3 and EPUB2 meta element.
# https://www.w3.org/TR/epub-33/#sec-meta-elem
class Meta(BasePackageModel, tag="meta"):
    content: Optional[str] = attr(name="content", default=None)
    dir: Optional[str] = attr(name="dir", default=None)
    http_equiv: Optional[str] = attr(name="http-equiv", default=None)
    id: Optional[str] = attr(name="id", default=None)
    lang: Optional[str] = attr(name="lang", ns=NS_XML, default=None)
    name: Optional[str] = attr(name="name", default=None)
    # https://www.w3.org/TR/epub-33/#sec-property-datatype
    property: Optional[str] = attr(name="property", default=None)
    refines: Optional[str] = attr(name="refines", default=None)
    scheme: Optional[str] = attr(name="scheme", default=None)

    value: Annotated[Optional[str], StringConstraints(strip_whitespace=True)] = None


class Link(BasePackageModel, tag="link"):
    href: str = attr(name="href")
    rel: str = attr(name="rel")

    href_lang: Optional[str] = attr(name="hreflang", default=None)
    id: Optional[str] = attr(name="id", default=None)
    media_type: Optional[str] = attr(name="media-type", default=None)
    properties: Optional[str] = attr(name="properties", default=None)
    refines: Optional[str] = attr(name="refines", default=None)


# https://www.w3.org/TR/epub-33/#sec-metadata-elem
class Metadata(BasePackageModel, tag="metadata", search_mode='unordered'):
    identifier: List[Identifier] = element(tag="identifier", ns=NS_DC)
    language: List[Language] = element(tag="language", ns=NS_DC)
    # Relax EPUB3 spec and make it optional to support EPUB2.
    meta: List[Meta] = element(tag="meta", default=[])
    title: List[Element] = element(tag="title", ns=NS_DC)

    link: List[Link] = element(tag="link", default=[])

    contributor: List[Element] = element(tag="contributor", default=[])
    coverage: List[Element] = element(tag="coverage", default=[])
    creator: List[Element] = element(tag="creator", default=[])
    date: List[Element] = element(tag="date", default=[])
    description: List[Element] = element(tag="description", default=[])
    format: List[Element] = element(tag="format", default=[])
    publisher: List[Element] = element(tag="publisher", default=[])
    relation: List[Element] = element(tag="relation", default=[])
    rights: List[Element] = element(tag="rights", default=[])
    source: List[Element] = element(tag="source", default=[])
    subject: List[Element] = element(tag="subject", default=[])
    type: List[Element] = element(tag="type", default=[])


# https://www.w3.org/TR/epub-33/#sec-item-elem
class Item(BasePackageModel, tag="item"):
    href: str = attr(name="href")
    id: str = attr(name="id")
    media_type: str = attr(name="media-type")

    fallback: Optional[str] = attr(name="fallback", default=None)
    media_overlay: Optional[str] = attr(name="media-overlay", default=None)
    properties: Optional[str] = attr(name="properties", default=None)


# https://www.w3.org/TR/epub-33/#sec-pkg-manifest
class Manifest(BasePackageModel, tag="manifest"):
    id: Optional[str] = attr(name="id", default=None)

    item: List[Item] = element(tag="item")


# https://www.w3.org/TR/epub-33/#sec-itemref-elem
class ItemRef(BasePackageModel, tag="itemref"):
    id: Optional[str] = attr(name="id", default=None)
    linear: Optional[str] = attr(name="linear", default=None)
    properties: Optional[str] = attr(name="properties", default=None)

    idref: str = attr(name="idref")


# https://www.w3.org/TR/epub-33/#dfn-spine
class Spine(BasePackageModel, tag="spine"):
    id: Optional[str] = attr(name="id", default=None)
    page_progression_direction: Optional[str] = attr(name="page-progression-direction", default=None)
    toc: Optional[str] = attr(name="toc", default=None)

    items: List[ItemRef] = element(tag="itemref")


class Guide(BasePackageModel, tag="guide"):
    # Legacy element, ignoring it for now.
    pass


class Bindings(BasePackageModel, tag="bindings"):
    # Deprecated element, ignoring it for now.
    pass


# https://www.w3.org/TR/epub-33/#sec-collection-elem
class Collection(BasePackageModel, tag="collection"):
    role: str = attr(name="role")

    dir: Optional[str] = attr(name="dir", default=None)
    id: Optional[str] = attr(name="id", default=None)
    lang: Optional[str] = attr(name="lang", ns=NS_XML, default=None)


    metadata: Optional[Metadata] = element(tag="metadata", default=None)
    collections: List['Collection'] = element(tag="collection", default=[])
    links: List[Link] = element(tag="link")


# https://www.w3.org/TR/epub-33/#sec-package-elem
class Package(BasePackageModel, tag="package"):
    # Attributes
    unique_identifier: str = attr(name="unique-identifier")
    version: str = attr(name="version")

    dir: Optional[str] = attr(name="dir", default=None)
    id: Optional[str] = attr(name="id", default=None)
    lang: Optional[str] = attr(name="lang", ns="xml", default=None)
    prefix: Optional[str] = attr(name="prefix", default=None)

    # Content
    metadata: Metadata = element(tag="metadata")
    manifest: Manifest = element(tag="manifest")
    spine: Spine = element(tag="spine")

    guide: Optional[Guide] = element(tag="guide", default=None)
    bindings: Optional[Bindings] = element(tag="bindings", default=None)
    collection: List[Collection] = element(tag="collection", default=[])
