import json
import os

from dotenv import load_dotenv

from api.openlibrary.model import Edition
from api.openlibrary.service import OpenlibraryService
from common_lib.db import DBFactory


def test_author():
    load_dotenv()
    openlibrary_db = DBFactory(os.path.expandvars(os.getenv("OL_PG_URL")))
    openlibrary_svc = OpenlibraryService(db_factory=openlibrary_db)

    item = openlibrary_svc.autor_by_key("/authors/OL7778899A")
    print(json.dumps(item.model_dump(), indent=2))

def test_edition():
    load_dotenv()
    openlibrary_db = DBFactory(os.path.expandvars(os.getenv("OL_PG_URL")))
    openlibrary_svc = OpenlibraryService(db_factory=openlibrary_db)

    item = openlibrary_svc.edition_by_isbn("9781619634459")
    print(json.dumps(item.model_dump(), indent=2))

def test_book():
    edition = Edition.model_validate({"key": "key", "title": "title"})
