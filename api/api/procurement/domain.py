from pydantic import BaseModel, Field, ConfigDict


class IdMatch(BaseModel):
    model_config = ConfigDict(frozen=True)

    type: str = Field(description="Type of ID, e.g. isbn, uuid, asin etc.")
    value: str = Field(description="The ID which matched the other EPUB book.")
    other_book_id: int = Field(description="ID of the other EPUB book.")
