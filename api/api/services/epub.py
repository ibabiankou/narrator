import logging
import zipfile
from io import BytesIO
from typing import Annotated, Tuple, Dict, List
from zipfile import ZipFile

from bs4 import BeautifulSoup

from api.models.narration import NarrationManifest, ContentFile, NavigationItem, AudioTrack
from api.utils.imgproxy import ImgProxy
from common_lib.service import Service
from epub_lib import Epub
from epub_lib.model.nav import PublicationContent
from epub_lib.model.tts import FragmentList
from epub_lib.util.tts import process_xhtml_inplace

LOG = logging.getLogger(__name__)


class EpubService(Service):
    """Service for processing EPUB files in-memory."""

    def __init__(self, **kwargs):
        self.img_proxy = ImgProxy()

    def remove_links(self, file_bytes: BytesIO) -> BytesIO:
        src_epub = Epub(file_bytes)
        files_to_clean = set(src_epub.get_spine_files())

        file_bytes.seek(0)
        src_zip_file: ZipFile = ZipFile(file_bytes)

        out_bytes = BytesIO()
        with ZipFile(out_bytes, "w", zipfile.ZIP_DEFLATED) as out_zip:
            out_zip.writestr("mimetype", src_zip_file.read("mimetype"), compress_type=zipfile.ZIP_STORED)

            for fileinfo in src_zip_file.infolist():
                if fileinfo.is_dir():
                    continue

                LOG.debug("Processing %s", fileinfo.filename)

                if fileinfo.filename == "mimetype":
                    LOG.debug("Skipping %s file...", fileinfo.filename)
                    continue

                # TODO: make it more robust/configurable. Use regexp.
                if fileinfo.filename == "oceanofpdf.com":
                    LOG.debug("Skipping %s file...", fileinfo.filename)
                    continue

                if fileinfo.filename in files_to_clean:
                    out_zip.writestr(fileinfo.filename, self._clean_file(src_zip_file.read(fileinfo.filename)))
                else:
                    out_zip.writestr(fileinfo.filename, src_zip_file.read(fileinfo.filename))

        out_bytes.seek(0)
        LOG.debug("Compression ratio: %s", len(out_bytes.getvalue()) / len(file_bytes.getvalue()))
        return out_bytes

    def _clean_file(self, spine_file_bytes: bytes) -> bytes:
        soup = BeautifulSoup(spine_file_bytes, "xml")
        str(soup)
        for anc in soup.find_all("a", attrs={"href": True}):
            # TODO: make it more robust/configurable. Use regexp.
            if "oceanofpdf" in anc.get("href"):
                LOG.debug("Found tag to remove %s", anc)
                should_continue = True
                current = anc
                while should_continue:
                    parent = current.parent
                    LOG.debug("Decomposing %s", current)
                    current.decompose()
                    should_continue = parent is not None and len(parent.contents) == 0
                    current = parent

        return soup.encode(formatter="minimal")

    def inline_fragments(self, file_bytes: BytesIO) -> Tuple[BytesIO, Dict[str, FragmentList]]:
        LOG.debug("Inlining fragments...")
        src_epub = Epub(file_bytes)
        content_files = src_epub.get_spine_files()

        file_bytes.seek(0)
        src_zip_file: ZipFile = ZipFile(file_bytes)

        out_bytes = BytesIO()
        with ZipFile(out_bytes, "w", zipfile.ZIP_DEFLATED) as out_zip:
            out_zip.writestr("mimetype", src_zip_file.read("mimetype"), compress_type=zipfile.ZIP_STORED)

            fragment_id = 0
            fragment_map = {}
            for file in content_files:
                content_file_bytes, file_fragments, last_fragment_id = process_xhtml_inplace(src_zip_file.read(file),
                                                                                             fragment_id)
                fragment_id = last_fragment_id + 1
                fragment_map[file] = file_fragments
                out_zip.writestr(file, content_file_bytes)

            for fileinfo in src_zip_file.infolist():
                if fileinfo.is_dir():
                    continue

                LOG.debug("Processing %s", fileinfo.filename)

                if fileinfo.filename in content_files:
                    LOG.debug("Skipping %s file...", fileinfo.filename)
                    continue

                if fileinfo.filename == "mimetype":
                    LOG.debug("Skipping %s file...", fileinfo.filename)
                    continue

                if fileinfo.filename in content_files:
                    # Content files are already processed.
                    continue
                else:
                    out_zip.writestr(fileinfo.filename, src_zip_file.read(fileinfo.filename))

        out_bytes.seek(0)
        LOG.debug("Compression ratio: %s", len(out_bytes.getvalue()) / len(file_bytes.getvalue()))
        return out_bytes, fragment_map

    def build_narration_manifest(
            self, publication_content: PublicationContent, fragment_map: Dict[str, FragmentList]) -> NarrationManifest:

        narration_manifest_items: List[ContentFile] = []
        for spine_item in publication_content.spine_items:
            if spine_item.href not in fragment_map:
                raise ValueError(f"Spine item '{spine_item.href}' is missing from fragment map.")
            # noinspection PyTypeChecker
            all_fragments: FragmentList = fragment_map.get(spine_item.href)

            # TODO: implement smarter logic to suggest whether to narrate this content.
            should_narrate = True

            if len(spine_item.navigation_items) == 0:
                item = NavigationItem(
                    title=spine_item.title or "Unknown",
                    # Some items might be empty, e.g. cover page usually only has an image and no text.
                    audio_tracks=[] if len(all_fragments.root) == 0 else AudioTrack.split_into_tracks(
                        all_fragments.root),
                    narrate=should_narrate,
                )
                content_file = ContentFile(
                    href=spine_item.href,
                    title=spine_item.title,
                    epub_types=spine_item.epub_types,
                    navigation_items=[item]
                )
            elif len(spine_item.navigation_items) == 1:
                nav_item = spine_item.navigation_items[0]
                item = NavigationItem(
                    idref=nav_item.idref,
                    title=nav_item.title,
                    # Some items might be empty, e.g. cover page usually only has an image and no text.
                    audio_tracks=[] if len(all_fragments.root) == 0 else AudioTrack.split_into_tracks(
                        all_fragments.root),
                    narrate=should_narrate,
                )
                content_file = ContentFile(
                    href=spine_item.href,
                    title=spine_item.title,
                    epub_types=spine_item.epub_types,
                    navigation_items=[item]
                )
            else:  # multiple nav items, so need to split fragments based on idrefs from nav items.
                reversed_nav_items: List[NavigationItem] = []
                for nav_item in reversed(spine_item.navigation_items):
                    item_fragments = all_fragments.remove_all_by_visited_id(nav_item.idref)

                    if len(item_fragments) == 0:
                        LOG.warning("Spine item:\n%s", spine_item)
                        LOG.warning("Nav item:\n%s", nav_item)
                        LOG.warning("Processed nav_items:\n%s", list(reversed(reversed_nav_items)))
                        LOG.warning("Remaining fragments:\n%s", all_fragments.root)
                        raise ValueError(f"Nav item has no fragments.")

                    item = NavigationItem(
                        idref=nav_item.idref,
                        title=nav_item.title,
                        audio_tracks=AudioTrack.split_into_tracks(item_fragments),
                        narrate=should_narrate,
                    )
                    reversed_nav_items.append(item)

                if len(all_fragments.root) > 0:
                    LOG.info("Got fragments after processing nav items. Adding a fake nav item...")
                    item = NavigationItem(
                        title=spine_item.title or "Unknown",
                        audio_tracks=AudioTrack.split_into_tracks(all_fragments.root),
                        narrate=should_narrate,
                    )
                    reversed_nav_items.append(item)

                content_file = ContentFile(
                    href=spine_item.href,
                    title=spine_item.title,
                    epub_types=spine_item.epub_types,
                    navigation_items=[n for n in reversed(reversed_nav_items)]
                )

            narration_manifest_items.append(content_file)

        # Verify all fragments are in ascending order.
        last_seen_id = -1
        for content_file in narration_manifest_items:
            for nav_item in content_file.navigation_items:
                for audio_track in nav_item.audio_tracks:
                    for frag in audio_track.fragments.root:
                        # Drop all visited_ids from fragments.
                        frag.visited_ids = []

                        if last_seen_id >= frag.id:
                            LOG.warning("Content file: %s", content_file.href)
                            LOG.warning("Nav item: %s", nav_item.idref)
                            LOG.warning("Track: %s", audio_track.name)
                            raise ValueError(f"Fragment id {frag.id} is not in ascending order.")
                        last_seen_id = frag.id


        # noinspection PyArgumentList
        return NarrationManifest(narration_manifest_items)


EpubServiceDep = Annotated[EpubService, EpubService.dep()]
