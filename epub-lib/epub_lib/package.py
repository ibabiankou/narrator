"""Model definition for Open Packaging Format."""
from typing import List, Optional, Annotated

from pydantic import StringConstraints
from pydantic_xml import BaseXmlModel, element, attr

NS_OPF_URL = "http://www.idpf.org/2007/opf"
NS_OPF = "opf"
NS_DC_URL = "http://purl.org/dc/elements/1.1/"
NS_DC = "dc"
NS_XSI_URL = "http://www.w3.org/2001/XMLSchema-instance"
NS_XSI = "xsi"
NS_XML_URL = "http://www.w3.org/XML/1998/namespace"
NS_XML = "xml"
PACKAGE_NS_MAP = {
    "": NS_OPF_URL,
    NS_OPF: NS_OPF_URL,
    NS_DC: NS_DC_URL,
    NS_XSI: NS_DC_URL,
    NS_XML: NS_XML_URL,
}


class Identifier(BaseXmlModel, tag="identifier", ns=NS_DC, nsmap=PACKAGE_NS_MAP):
    id: str = attr(name="id")

    value: Annotated[str, StringConstraints(strip_whitespace=True)]


class Title(BaseXmlModel, tag="title", ns=NS_DC, nsmap=PACKAGE_NS_MAP):
    id: Optional[str] = attr(name="id", default=None)
    lang: Optional[str] = attr(name="lang", ns=NS_XML, default=None)
    dir: Optional[str] = attr(name="dir", default=None)

    value: Annotated[str, StringConstraints(strip_whitespace=True)]


class Language(BaseXmlModel, tag="language", ns=NS_DC, nsmap=PACKAGE_NS_MAP):
    id: Optional[str] = attr(name="id", default=None)

    value: Annotated[str, StringConstraints(strip_whitespace=True)]


class Meta(BaseXmlModel, tag="meta", nsmap=PACKAGE_NS_MAP):
    # https://www.w3.org/TR/epub-33/#sec-property-datatype
    property: str = attr(name="property")

    id: Optional[str] = attr(name="id", default=None)
    lang: Optional[str] = attr(name="lang", ns=NS_XML, default=None)
    dir: Optional[str] = attr(name="dir", default=None)
    refines: Optional[str] = attr(name="refines", default=None)
    scheme: Optional[str] = attr(name="scheme", default=None)

    value: Annotated[str, StringConstraints(strip_whitespace=True)]


class Link(BaseXmlModel, tag="link", nsmap=PACKAGE_NS_MAP):
    href_lang: Optional[str] = attr(name="hreflang", default=None)
    id: Optional[str] = attr(name="id", default=None)
    media_type: Optional[str] = attr(name="media-type", default=None)
    properties: Optional[str] = attr(name="properties", default=None)
    refines: Optional[str] = attr(name="refines", default=None)

    rel: str = attr(name="rel")
    href: str = attr(name="href")


# https://www.w3.org/TR/epub-33/#sec-metadata-elem
class Metadata(BaseXmlModel, tag="metadata", search_mode='unordered', nsmap=PACKAGE_NS_MAP):
    identifier: List[Identifier] = element(tag="identifier", ns=NS_DC)
    title: List[Title] = element(tag="title", ns=NS_DC)
    language: List[Language] = element(tag="language", ns=NS_DC)

    meta: List[Meta] = element(tag="meta")
    link: List[Link] = element(tag="link", default=[])


# https://www.w3.org/TR/epub-33/#sec-item-elem
class Item(BaseXmlModel, tag="item", nsmap=PACKAGE_NS_MAP):
    id: str = attr(name="id")
    href: str = attr(name="href")
    media_type: str = attr(name="media-type")
    fallback: Optional[str] = attr(name="fallback", default=None)

    media_overlay: Optional[str] = attr(name="media-overlay", default=None)
    properties: Optional[str] = attr(name="properties", default=None)


# https://www.w3.org/TR/epub-33/#sec-pkg-manifest
class Manifest(BaseXmlModel, tag="manifest", nsmap=PACKAGE_NS_MAP):
    id: Optional[str] = attr(name="id", default=None)

    item: List[Item] = element(tag="item")


# https://www.w3.org/TR/epub-33/#sec-itemref-elem
class ItemRef(BaseXmlModel, tag="itemref", nsmap=PACKAGE_NS_MAP):
    id: Optional[str] = attr(name="id", default=None)
    linear: Optional[str] = attr(name="linear", default=None)
    properties: Optional[str] = attr(name="properties", default=None)

    idref: str = attr(name="idref")


# https://www.w3.org/TR/epub-33/#dfn-spine
class Spine(BaseXmlModel, tag="spine", nsmap=PACKAGE_NS_MAP):
    id: Optional[str] = attr(name="id", default=None)
    page_progression_direction: Optional[str] = attr(name="page-progression-direction", default=None)
    toc: Optional[str] = attr(name="toc", default=None)

    items: List[ItemRef] = element(tag="itemref")


class Guide(BaseXmlModel, tag="guide", nsmap=PACKAGE_NS_MAP):
    # Legacy element, ignoring it for now.
    pass


class Bindings(BaseXmlModel, tag="bindings", nsmap=PACKAGE_NS_MAP):
    # Deprecated element, ignoring it for now.
    pass


# https://www.w3.org/TR/epub-33/#sec-collection-elem
class Collection(BaseXmlModel, tag="collection", nsmap=PACKAGE_NS_MAP):
    id: Optional[str] = attr(name="id", default=None)
    lang: Optional[str] = attr(name="lang", ns=NS_XML, default=None)
    dir: Optional[str] = attr(name="dir", default=None)

    role: str = attr(name="role")

    metadata: Optional[Metadata] = element(tag="metadata", default=None)
    collections: List['Collection'] = element(tag="collection", default=[])
    links: List[Link] = element(tag="link")


# https://www.w3.org/TR/epub-33/#sec-package-elem
class Package(BaseXmlModel, tag="package", nsmap=PACKAGE_NS_MAP):
    # Attributes
    version: str = attr(name="version")
    unique_identifier: str = attr(name="unique-identifier")

    id: Optional[str] = attr(name="id", default=None)
    lang: Optional[str] = attr(name="lang", ns="xml", default=None)
    dir: Optional[str] = attr(name="dir", default=None)

    prefix: Optional[str] = attr(name="prefix", default=None)

    # Content
    metadata: Metadata = element(tag="metadata")
    manifest: Manifest = element(tag="manifest")
    spine: Spine = element(tag="spine")

    guide: Optional[Guide] = element(tag="guide", default=None)
    bindings: Optional[Bindings] = element(tag="bindings", default=None)
    collection: List[Collection] = element(tag="collection", default=[])
