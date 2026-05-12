import logging
import os

from requests import JSONDecodeError, HTTPError

from api.models import api
from scripts.auth import session

LOG = logging.getLogger(__name__)


class NNarrator:
    def __init__(self, base_url: str = "https://nnarrator.eu/api"):
        # TODO: make it auto-refresh tokens.
        self.session = session(base_url)

    def _get(self, url: str, params: dict = None):
        response = self.session.get(url, params=params)
        try:
            response.raise_for_status()
            return response.json()
        except HTTPError as e:
            LOG.error("Got HTTP error. Status: %s %s", response.status_code, response.reason)
            LOG.warning("Request URL: %s", response.request.url)
            LOG.warning("Request Headers: %s", response.request.headers)
            raise e

        except JSONDecodeError as e:
            LOG.error("Failed to parse JSON from response. Status: %s %s", response.status_code, response.reason)
            raise e

    def get_all_books(self, page_size: int = 100) -> list[api.BookOverview]:
        books = []
        keep_going = True
        page_index = 0

        # Go through all pages
        while keep_going:
            params = {
                "page_index": page_index,
                "size": page_size
            }
            response_data = self._get("books/", params=params)
            page = api.PagedResponse[api.BookOverview].model_validate(response_data)

            books.extend(page.items)
            keep_going = page.page_info.total > page.page_info.size * (page.page_info.index + 1)
            if keep_going:
                page_index += 1

        return books

    def get_file(self, file_key: str, dest_dir: str):
        with self.session.get(f"files/{file_key}", stream=True) as response:
            try:
                response.raise_for_status()
                file_name = file_key.split('/')[-1]
                with open(os.path.join(dest_dir, file_name), "wb") as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
            except HTTPError as e:
                LOG.error("Got HTTP error. Status: %s %s", response.status_code, response.reason)
                LOG.warning("Request URL: %s", response.request.url)
                LOG.warning("Request Headers: %s", response.request.headers)
                raise e

    def procurement_upload(self, file_path: str):
        with open(file_path, 'rb') as f:
            files = {'file': f}
            response = self.session.post("procurement/upload", files=files)
            response.raise_for_status()
