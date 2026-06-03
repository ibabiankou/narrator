import logging
import zipfile
from io import BytesIO
from typing import Annotated, Tuple, Dict
from zipfile import ZipFile

from bs4 import BeautifulSoup

from api.utils.imgproxy import ImgProxy
from common_lib.service import Service
from epub_lib import Epub
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
                content_file_bytes, file_fragments, last_fragment_id = process_xhtml_inplace(src_zip_file.read(file), fragment_id)
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


EpubServiceDep = Annotated[EpubService, EpubService.dep()]
