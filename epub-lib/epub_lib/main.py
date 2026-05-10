import logging
import os
from logging.config import dictConfig
from typing import List
from zipfile import ZipFile

from epub_lib.model.container import Container
from epub_lib.model.package import Package

LOGGING_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'standard': {
            'format': '%(asctime)s [%(levelname)s] %(name)s: %(message)s',
            'datefmt': '%Y-%m-%d %H:%M:%S'
        },
        'detailed': {
            'format': '%(asctime)s [%(levelname)s] %(name)s:%(lineno)d: %(message)s'
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'stream': 'ext://sys.stdout',
            'formatter': 'standard',
            'level': 'INFO',
        },
    },
    'loggers': {
        '': {  # Root logger
            'handlers': ['console'],
            'level': 'DEBUG',
        },
    }
}

dictConfig(LOGGING_CONFIG)
LOG = logging.getLogger(__name__)

dir_with_books = "../../out/epub"
CONTAINER_XML = "META-INF/container.xml"


def all_files(dir: str) -> list[str]:
    files = []
    for filename in os.listdir(dir):
        if filename.endswith(".epub"):
            abs_file_path = os.path.abspath(os.path.join(dir, filename))
            files.append(abs_file_path)
    return files


def get_root_files(epub: ZipFile) -> List[str]:
    LOG.debug("Reading and parsing %s", CONTAINER_XML)
    with epub.open(CONTAINER_XML) as container_file:
        try:
            container = Container.from_xml(container_file.read())
            root_files = [i.full_path for i in container.root_files.items]
            if len(root_files) > 1:
                LOG.warning("'%s' has %s root files in container.xml: %s",
                            epubf.filename,
                            len(root_files),
                            root_files)
            return root_files
        except Exception as e:
            LOG.error("Failed to parse containers.xml", e)
            return []


def get_package(epub: ZipFile, root_file: str) -> Package:
    with epub.open(root_file) as package_file:
        try:
            package_xml = package_file.read()
            return Package.from_xml(package_xml)
        except Exception as e:
            LOG.error("Failed to parse root_file of %s", epub.filename, e)
            LOG.error("Raw content of %s:\n%s", root_file, package_xml.decode("utf-8"))
            raise e


if __name__ == "__main__":
    all_books = all_files(dir_with_books)
    LOG.info("Found %s books: \n  %s", len(all_books), "\n  ".join(all_books))

    for book_file in all_books:
        LOG.info("Processing: %s", book_file)
        with ZipFile(book_file) as epubf:
            # Get the root files from the META-INF/container.xml
            root_files = get_root_files(epubf)

            # Parse the default root file.
            package = get_package(epubf, root_files[0])
            LOG.info("Got '%s'", [t.value for t in package.metadata.title])

    print("Done...")
