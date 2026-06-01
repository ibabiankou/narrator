import logging
from typing import Optional, List, Dict, Set

from pydantic import BaseModel

from epub_lib.model.ncx import NavPoint
from epub_lib.model.package import Item

LOG = logging.getLogger(__name__)


# Types to represent EPUB3 model of navigation.
class TocItem(BaseModel):
    href: str
    title: str


class TableOfContent(BaseModel):
    items: List[TocItem]


class TocItemBuilder:
    full_href: str
    path_only_href: str
    id: Optional[str] = None
    title: Optional[str] = None
    epub_type: Optional[str] = None

    def __init__(self, href: str, idref: Optional[str]):
        self.full_href = href
        self.path_only_href = href.split("#")[0]
        self.id = idref

    def build(self) -> TocItem:
        return TocItem(href=self.full_href, id=self.id, title=self.title, epub_type=self.epub_type)


class TocBuilder:
    def __init__(self):
        self.items: List[TocItemBuilder] = []
        self.item_map: Dict[str, TocItemBuilder] = {}

    def add_manifest_item(self, item: Item):
        toc_item = TocItemBuilder(href=item.href, idref=item.id)
        self.items.append(toc_item)
        self.item_map[item.id] = toc_item

    def contains(self, idref: str) -> bool:
        return idref in self.item_map

    def add_toc_item(self, toc_item: TocItem):
        if toc_item.id is not None:
            if self.contains(toc_item.id):
                self.item_map[toc_item.id].title = toc_item.title
            else:
                LOG.warning("Item referenced by Table of Content '%s' is not in the spine.", toc_item.id)
            return
        if toc_item.title:
            self._add_title(toc_item.href, toc_item.title)

    def _add_title(self, href: str, title: str):
        full_href = href
        path_only_href = href.split("#")[0]

        # Check for full href match.
        for item in self.items:
            if item.full_href == full_href:
                item.title = title
                return

        # Check for partial href match (base path only).
        matches = []
        for item in self.items:
            if item.path_only_href == path_only_href:
                matches.append(item)
        # Only use partial match if got a single item.
        if len(matches) == 1:
            matches[0].title = title
            return

    def add_nav_point(self, nav_point: NavPoint):
        self._add_title(nav_point.content.src, nav_point.nav_label.text)

    def build(self):
        return TableOfContent(items=[item.build() for item in self.items])


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
