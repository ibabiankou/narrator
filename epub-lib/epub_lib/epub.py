import logging
from os import PathLike
from typing import IO, List
from zipfile import ZipFile

from epub_lib.model.container import CONTAINER_XML, Container
from epub_lib.model.package import Package

LOG = logging.getLogger(__name__)


class Epub:
    def __init__(self, file: str | PathLike[str] | IO[bytes]):
        self.zip_file = ZipFile(file)
        self.root_files = self._get_root_files(self.zip_file)
        self.package = self._get_package(
            self.zip_file,
            self.root_files[0]
        )

    def _get_root_files(self, epub: ZipFile) -> List[str]:
        LOG.debug("Reading and parsing %s", CONTAINER_XML)
        with epub.open(CONTAINER_XML) as container_file:
            container = Container.from_xml(container_file.read())
            return [i.full_path for i in container.root_files.items]

    def _get_package(self, epub: ZipFile, root_file: str) -> Package:
        LOG.debug("Reading and parsing root file %s", root_file)
        with epub.open(root_file) as package_file:
            package_xml = package_file.read()
            return Package.from_xml(package_xml)
