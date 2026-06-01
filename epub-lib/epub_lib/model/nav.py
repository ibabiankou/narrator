import logging
from typing import Optional, List, Dict, Set

from pydantic import BaseModel

from epub_lib.model.package import Item

LOG = logging.getLogger(__name__)


# Types to represent EPUB3 model of navigation.
class TocItem(BaseModel):
    href: str
    title: str


class TableOfContent(BaseModel):
    items: List[TocItem]


# Types to merge physical (files referenced in spine/manifest) and logical (NCX/ToC references) representations.
class NavigationItem(BaseModel):
    # ID of an HTML element within a manifest item where a logical piece of the publication starts.
    idref: Optional[str] = None
    title: str


class SpineItem(BaseModel):
    # Path to an HTML file with actual content as defined in the Manifest.
    href: str
    # HTML Title extracted from this manifest item.
    title: Optional[str] = None

    # All values of epub:type attribute found in the document.
    epub_types: List[str] = []

    navigation_items: List[NavigationItem] = []


class PublicationContent(BaseModel):
    spine_items: List[SpineItem]


class PublicationContentBuilder:
    def __init__(self):
        self.spine_items: List[SpineItem] = []
        self.href_map: Dict[str, SpineItem] = {}
        self.processed_manifest_ids: Set[str] = set()

    def add_manifest_item(self, item: Item):
        spine_item = SpineItem(href=item.href)
        self.spine_items.append(spine_item)
        self.processed_manifest_ids.add(item.id)

        href = spine_item.href
        if "#" in href:
            LOG.warning("Manifest item contains fragment: '%s'", item)
            href = href.split("#")[0]

        if href in self.href_map:
            LOG.warning("Duplicate manifest item detected: '%s'", item)

        self.href_map[href] = spine_item

    def contains(self, idref: str) -> bool:
        return idref in self.processed_manifest_ids

    def add_navigation_item(self, href: str, title: str):
        base_href = href
        idref = None

        if "#" in href:
            href_components = href.split("#")
            base_href = href_components[0]
            idref = href_components[1]

        spine_item_maybe = self.href_map.get(base_href)
        if spine_item_maybe is not None:
            nav_item = NavigationItem(idref=idref, title=title)
            spine_item_maybe.navigation_items.append(nav_item)
        else:
            LOG.warning("Navigation item '%s' is referencing unknown spine item.", href)

    def build(self) -> PublicationContent:
        return PublicationContent(spine_items=self.spine_items)
