import json
import os

from dotenv import load_dotenv

from api.openlibrary.model import Edition
from api.openlibrary.service import OpenlibraryService
from common_lib.db import DBFactory

load_dotenv()
openlibrary_db = DBFactory(os.path.expandvars(os.getenv("OL_PG_URL")))
openlibrary_svc = OpenlibraryService(None, db_factory=openlibrary_db)

class TestService:
    def test_author(self):
        item = openlibrary_svc.autor_by_key("/authors/OL7778899A")
        print(json.dumps(item.model_dump(), indent=2))

    def test_edition(self):
        item = openlibrary_svc.edition_by_isbn("9781619634459")
        print(json.dumps(item.model_dump(), indent=2))

    def test_book(self):
        edition = Edition.model_validate({"key": "key", "title": "title"})
