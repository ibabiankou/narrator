import logging
import os

from google import genai
from google.genai.types import HttpOptions, HttpRetryOptions
from pydantic import BaseModel, Field
from typing import List, Optional

from api.models import domain
from api.utils.isbn import clean_isbn, validate_isbn


LOG = logging.getLogger(__name__)


class BookMetadata(BaseModel):
    title: Optional[str] = Field(default=None, description="The full title of the book.")
    series: Optional[str] = Field(default=None, description="The name of the series.")
    authors: List[str] = Field(default=[], description="A list of authors of the book.")
    isbns: List[str] = Field(default=[], description="The 10 or 13-digit ISBN(s) if found in the text.")


client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"),
                      http_options=HttpOptions(retry_options=HttpRetryOptions(attempts=10,
                                                                              http_status_codes=[408, 429, 500, 502,
                                                                                                 503, 504])))

def remove_invalid_isbns(raw_isbns: list[str]):
    result = []
    for raw_isbn in raw_isbns:
        isbn = clean_isbn(raw_isbn)
        if validate_isbn(isbn):
            result.append(isbn)
    return result

def identify_book(book_text_sample: str) -> Optional[domain.BookMetadata]:
    prompt = f"""
    Help me to keep track of my books. Analyze the following text from the beginning of a book. 
    Identify the book and extract its metadata (title, series, authors, ISBNs).
    Return null value for the fields with low confidence. Only include data present in the text.
    
    Text:
    {book_text_sample}
    """

    response = client.models.generate_content(
        model="gemini-3.1-flash-lite-preview",
        contents=prompt,
        config={
            "response_mime_type": "application/json",
            "response_schema": BookMetadata,
        }
    )
    metadata: Optional[BookMetadata] = response.parsed

    if metadata is None:
        LOG.warning("Response does not have parsed data.")
        if response.candidates and len(response.candidates) > 0:
            resp_candidate = response.candidates[0]
            LOG.warning("LLM finished without response. Reason: '%s'. Message: '%s'",
                        resp_candidate.finish_reason,
                        resp_candidate.finish_message)
        else:
            LOG.warning("Response does not have any candidates. Prompt feedback: %s", response.prompt_feedback)
        return None

    return domain.BookMetadata(title=metadata.title,
                               series=metadata.series,
                               authors=metadata.authors,
                               isbns=remove_invalid_isbns(metadata.isbns))
