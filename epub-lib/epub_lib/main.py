import logging
import os
from logging.config import dictConfig
from typing import List
from zipfile import ZipFile

from epub_lib.container import Container

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


def get_root_files(container_xml) -> List[str]:
    try:
        container = Container.from_xml(container_xml)
        if len(container.root_files.items) > 1:
            LOG.warning("Got a book with %s root files in container.xml", len(container.root_files.items))
        return [i.full_path for i in container.root_files.items]
    except Exception as e:
        LOG.error("Failed to parse containers.xml", e)
        return []


if __name__ == "__main__":
    all_books = all_files(dir_with_books)
    LOG.info("Found %s books: \n  %s", len(all_books), "\n  ".join(all_books))

    for book_file in all_books:
        LOG.info("Processing: %s", book_file)
        with ZipFile(book_file) as epubf:
            LOG.info("Reading and parsing %s", CONTAINER_XML)
            with epubf.open(CONTAINER_XML) as containerf:
                root_files = get_root_files(containerf.read())
                LOG.info("Got %s root files %s", len(root_files), root_files)
                # TODO: If there are more than one root file, default to the first one.

            # Parse the root file.


    print("Done...")
