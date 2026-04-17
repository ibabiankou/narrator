import os
from google import genai
from pydantic import BaseModel, Field
from typing import List

class BookMetadata(BaseModel):
    title: str = Field(description="The full title of the book.")
    series: str = Field(description="The name of the series.")
    authors: List[str] = Field(description="A list of authors of the book.")
    isbn: List[str] = Field(description="The 10 or 13-digit ISBN(s) if found in the text.")

client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

def identify_book(book_text_sample: str) -> BookMetadata:
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

    return response.parsed
