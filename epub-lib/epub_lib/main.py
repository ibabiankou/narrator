import logging
import os
from logging.config import dictConfig

from epub_lib import Epub

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


def all_files(dir: str) -> list[str]:
    files = []
    for filename in os.listdir(dir):
        if filename.endswith(".epub"):
            abs_file_path = os.path.abspath(os.path.join(dir, filename))
            files.append(abs_file_path)
    return files


if __name__ == "__main__":
    all_books = all_files(dir_with_books)
    LOG.info("Found %s books: \n  %s", len(all_books), "\n  ".join(all_books))

    for book_file in all_books:
        LOG.info("Processing: %s", book_file)
        epub = Epub(book_file)

        LOG.info("Titles: '%s'", [t.value for t in epub.package.metadata.title])
        LOG.debug(epub.package.metadata.model_dump_json(indent=2, exclude_none=True))

    print("Done...")
