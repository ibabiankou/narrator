import os

from google import genai
from google.genai.types import HttpOptions, HttpRetryOptions
from pydantic import BaseModel, Field
from typing import List, Optional

from api.models import domain
from api.utils.isbn import clean_isbn


class BookMetadata(BaseModel):
    title: Optional[str] = Field(default=None, description="The full title of the book.")
    series: Optional[str] = Field(default=None, description="The name of the series.")
    authors: List[str] = Field(default=[], description="A list of authors of the book.")
    isbns: List[str] = Field(default=[], description="The 10 or 13-digit ISBN(s) if found in the text.")


client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"),
                      http_options=HttpOptions(retry_options=HttpRetryOptions(attempts=10,
                                                                              http_status_codes=[408, 429, 500, 502,
                                                                                                 503, 504])))


def identify_book(book_text_sample: str) -> domain.BookMetadata:
    prompt = f"""
    Analyze the following text from the beginning of a book. 
    Identify the book and extract its metadata.
    Return null value for the fields with low confidence.
    
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
    metadata: BookMetadata = response.parsed

    return domain.BookMetadata(title=metadata.title,
                               series=metadata.series,
                               authors=metadata.authors,
                               isbns=[clean_isbn(isbn) for isbn in metadata.isbns])
