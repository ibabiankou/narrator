import logging
import re
from io import BytesIO
from os import PathLike
from pathlib import Path
from typing import IO, List, Optional, Tuple
from zipfile import ZipFile

import imagehash
from PIL import Image
from bs4 import BeautifulSoup
from datasketch import MinHash
from lxml.etree import XMLSyntaxError
from pydantic import ValidationError

from epub_lib.model.container import CONTAINER_XML, Container
from epub_lib.model.nav import TocItem, TableOfContent, PublicationContentBuilder, PublicationContent
from epub_lib.model.ncx import NavigationControl
from epub_lib.model.package import Package

LOG = logging.getLogger(__name__)


class Epub:
    def __init__(self, file: str | PathLike[str] | IO[bytes], filename: str = None):
        self.filename = filename
        self.zip_file: ZipFile = ZipFile(file)
        self.root_files = self._get_root_files(self.zip_file)
        self.root_file = self.root_files[0]
        self.root_file_dir: Path = Path(self.root_file).parent
        self.package = self._get_package(self.zip_file, self.root_file)
        self.manifest_item_dict = {i.id: i for i in self.package.manifest.item}
        # TODO: Clean up by removing empty values.

    def _get_root_files(self, epub: ZipFile) -> List[str]:
        LOG.debug("Reading and parsing %s", CONTAINER_XML)
        with epub.open(CONTAINER_XML) as container_file:
            try:
                raw_bytes = container_file.read()
                container = Container.from_xml(raw_bytes)
            except ValidationError as e:
                LOG.debug("Raw contents of %s :\n%s", CONTAINER_XML, raw_bytes.decode())
                raise e
            return [i.full_path for i in container.root_files.items]

    def _get_package(self, epub: ZipFile, root_file: str) -> Package:
        LOG.debug("Reading and parsing root file %s", root_file)
        with epub.open(root_file) as package_file:
            package_xml = package_file.read()
            try:
                return Package.from_xml(package_xml)
            except XMLSyntaxError as e:
                LOG.debug("Raw contents of %s :\n%s", root_file, package_xml.decode())
                raise e
            except ValidationError as e:
                LOG.debug("Raw contents of %s :\n%s", root_file, package_xml.decode())
                raise e

    def get_spine_files(self) -> List[str]:
        items = []
        for spine_item in self.package.spine.items:
            item = self.package.manifest.get_item_by_id(spine_item.idref)
            items.append(self._resource_path(item.href))
        return items

    def get_publication_content(self) -> PublicationContent:
        """Returns a combination of physical and logical content of the book."""
        # Merge spine, ncx and toc items.
        builder = PublicationContentBuilder(self.root_file_dir)
        for spine_item in self.package.spine.items:
            if builder.contains(spine_item.idref):
                LOG.debug("Got a duplicate idref in spine: %s", spine_item.idref)
            else:
                manifest_item_maybe = self.manifest_item_dict.get(spine_item.idref)
                if manifest_item_maybe is None:
                    LOG.warning("Spine references item '%s' missing in manifest", spine_item.idref)
                    continue
                builder.add_manifest_item(manifest_item_maybe)

        # Feed TOC items
        epub_toc_maybe = self._get_table_of_content()
        if epub_toc_maybe is not None:
            for toc_item in epub_toc_maybe.items:
                builder.add_navigation_item(toc_item.href, toc_item.title)

        # Only process NCX if TOC is not available.
        if epub_toc_maybe is None:
            # Feed NCX items
            ncx_maybe = self._get_navigation_control()
            if ncx_maybe is not None:
                for nav_point in ncx_maybe.nav_map.points:
                    builder.add_navigation_item(nav_point.content.src, nav_point.nav_label.text)

        # Iterate over all items, parse the file, fill in missing details.
        for spine_item in builder.spine_items:
            with self.zip_file.open(self._resource_path(spine_item.href)) as item_file:
                soup = BeautifulSoup(item_file, "lxml")

                if not spine_item.title:
                    title_maybe = soup.find("title")
                    if title_maybe:
                        spine_item.title = title_maybe.text

                elements = soup.find_all(attrs={"epub:type": True})
                spine_item.epub_types.extend([el.get("epub:type") for el in elements])

        return builder.build()

    def _get_table_of_content(self) -> Optional[TableOfContent]:
        """Load EPUB 3 table of contents. None, if not available."""
        nav_item = self.package.manifest.get_item_by_property("nav")
        if nav_item:
            with self.zip_file.open(self._resource_path(nav_item.href)) as nav_file:
                soup = BeautifulSoup(nav_file, "lxml")
                nav_toc = soup.find("nav", attrs={"epub:type": "toc"})

                if not nav_toc:
                    LOG.warning("Failed to find nav tag in '%s'.", nav_item.href)
                    return None

                toc_items = []
                for link in nav_toc.find_all("a"):
                    toc_items.append(TocItem(
                        href=link.get("href"),
                        title=link.text
                    ))

                return TableOfContent(items=toc_items)

        LOG.warning("Failed to find manifest item with property 'nav'.")
        return None

    def _get_navigation_control(self) -> Optional[NavigationControl]:
        """Load EPUB 2 navigation control. None, if not available."""
        if self.package.spine.toc:
            toc_item = self.package.manifest.get_item_by_id(self.package.spine.toc)
            if toc_item:
                with self.zip_file.open(self._resource_path(toc_item.href)) as ncx_file:
                    return NavigationControl.from_xml(ncx_file.read())
            else:
                LOG.warning("Failed to get navigation item '%s' from manifest.", toc_item)

        LOG.debug("Navigation control not found.")
        return None

    def get_cover_phash(self) -> Optional[Tuple[str, str]]:
        """Returns path to cover image and its phash. None, if no cover image found."""
        cover_image_maybe = self.get_cover_image()
        if cover_image_maybe is None:
            return None
        image_name, mime_type, image_bytes = cover_image_maybe

        # Handle cover item being an html page.
        if "html" in mime_type:
            html_img_src = self._first_image_on_page(image_bytes.decode())
            if html_img_src is not None:
                LOG.debug("Assuming %s is the cover image.", html_img_src)
                with self.zip_file.open(self._resource_path(html_img_src)) as cover_file:
                    with Image.open(cover_file) as pil_image:
                        return html_img_src, str(imagehash.phash(pil_image))

        # Handle cover item being an image.
        if mime_type.startswith("image/"):
            with Image.open(BytesIO(image_bytes)) as pil_image:
                return image_name, str(imagehash.phash(pil_image))

        raise ValueError(
            f"Failed to find cover image corresponding to manifest item href: {image_name}, mime: {mime_type}")

    def _first_image_on_page(self, html_source: str) -> Optional[str]:
        soup = BeautifulSoup(html_source, "lxml")
        img_tags = soup.find_all("img")
        if len(img_tags) > 0:
            if len(img_tags) > 1:
                LOG.debug("Found %s images on page. Using the first with src.", len(img_tags))

            img_src_list = [t.get("src") for t in img_tags if t.has_attr("src")]
            # noinspection PyTypeChecker
            return img_src_list[0]

        image_tags = soup.find_all("image")
        if len(image_tags) > 0:
            if len(image_tags) > 1:
                LOG.debug("Found %s images on page. Using the first with href.", len(image_tags))
            for t in image_tags:
                for k, v in t.attrs.items():
                    if "href" in k:
                        # noinspection PyTypeChecker
                        return v

        return None

    def get_cover_image(self) -> Optional[Tuple[str, str, bytes]]:
        """Returns the path to the cover image, media type, and content bytes."""
        if self.package.version.startswith("2"):
            cover_image_maybe = self._v2_cover_image()
            if cover_image_maybe is None:
                return None

            cover_image, media_type = cover_image_maybe
            with self.zip_file.open(self._resource_path(cover_image)) as cover_file:
                LOG.debug("Found cover item %s of type %s", cover_image, media_type)
                return cover_image, media_type, cover_file.read()

        elif self.package.version.startswith("3"):
            # EPUB3 Suposed to have a manifest item with property containing "cover-image".
            for item in self.manifest_item_dict.values():
                if item.properties is not None and "cover-image" in item.properties:
                    with self.zip_file.open(self._resource_path(item.href)) as cover_file:
                        LOG.debug("Found cover item %s of type %s", item.href, item.media_type)
                        return item.href, item.media_type, cover_file.read()
            LOG.debug("No cover manifest item found.")
            return None
        else:
            LOG.debug("Unexpected EPUB version: %s.", self.package.version)
            return None

    def _resource_path(self, path: str) -> str:
        """Returns an absolute path to the resource within the zip file."""
        return str(self.root_file_dir.joinpath(path))

    def _v2_cover_image(self) -> Optional[Tuple[str, str]]:
        # EPUB2 Should have a meta tag with the name "cover" referencing a cover manifest item.
        cover_meta = [m for m in self.package.metadata.meta if m.name and m.name == "cover"]
        if cover_meta:
            if len(cover_meta) > 1:
                LOG.debug(
                    "Multiple cover meta tags found. Will use the first with content. %s",
                    cover_meta
                )
            cover_references = [m.content for m in cover_meta if m.content is not None]
            if not cover_references:
                LOG.debug("No cover meta tags with content found: %s", cover_meta)
                return None
            cover_reference = cover_references[0]

            cover_item_maybe = self.manifest_item_dict.get(cover_reference)
            if cover_item_maybe is None:
                LOG.debug("Cover item not found in manifest: %s", cover_reference)
                return None
            return cover_item_maybe.href, cover_item_maybe.media_type
        else:
            LOG.debug("No cover meta tags found: %s", self.package.metadata.meta)
            return None

    def calculate_minhash(self, num_samples=34, sample_size=300, num_perm=128) -> List[int]:
        # Go through spine and extract all the text.
        all_words = []
        for itemref in self.package.spine.items:
            idref = itemref.idref
            item = self.manifest_item_dict[idref]
            content_file_path = item.href
            try:
                with self.zip_file.open(self._resource_path(content_file_path)) as html_file:
                    words = self._extract_clean_text(html_file)
                    LOG.debug("Extracted %s words from %s", len(words), content_file_path)
                    all_words.extend(words)
            except KeyError:
                LOG.debug("Manifest item '%s' not found in zip file. Skipping it.", content_file_path)
        LOG.debug(
            "Extracted %s words from %s items.",
            len(all_words),
            len(self.package.spine.items))

        # Select samples.
        sample = self._get_stride_sample(all_words, num_samples, sample_size)

        # Calculate minhash
        return self._calculate_minhash(sample, num_perm)

    def _extract_clean_text(self, html_file: IO[bytes]):
        """Strip HTML and normalize text."""
        soup = BeautifulSoup(html_file, "lxml")
        text = soup.get_text(separator=" ")

        # Remove non-alphanumeric and lowercase
        text = re.sub(r'\W+', ' ', text).lower()
        return text.split()

    def _get_stride_sample(self, words: List[str], num_samples: int, sample_size: int):
        """Grab `num_samples` samples of `sample_size` words from across the book."""
        if len(words) <= (num_samples * sample_size):
            # Book is too short, use everything
            return words

        # Skip first 2% and last 5% (fluff/ads)
        # TODO: Use EPUB metadata to omit fluff more reliably.
        start_idx = int(len(words) * 0.02)
        end_idx = int(len(words) * 0.95)
        core_words = words[start_idx:end_idx]

        stride = (len(core_words) - sample_size) // (num_samples - 1)
        sample = []
        for i in range(num_samples):
            pos = i * stride
            sample.extend(core_words[pos: pos + sample_size])
        return sample

    def _calculate_minhash(self, words: List[str], num_perm: int = 128) -> List[int]:
        """Create the MinHash signature."""
        m = MinHash(num_perm=num_perm, seed=42)
        # Use 3-word shingles for better precision
        for i in range(len(words) - 2):
            shingle = " ".join(words[i: i + 3])
            m.update(shingle.encode('utf8'))

        # Get the 128 integers
        # noinspection PyUnresolvedReferences
        signature = m.hashvalues.tolist()
        return signature
