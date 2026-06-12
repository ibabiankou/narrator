from pydantic import BaseModel, Field


class IdMatch(BaseModel):
    matched_id: str = Field(description="Value of ID which matched the other EPUB book.")
    other_book_id: int = Field(description="ID of the other EPUB book.")
