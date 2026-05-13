from pydantic import BaseModel, Field, ConfigDict


class IdMatch(BaseModel):
    model_config = ConfigDict(frozen=True)

    type: str = Field(description="Type of ID, e.g. isbn, uuid, asin etc.")
    value: str = Field(description="The ID which matched the other EPUB book.")
    other_book_id: int = Field(description="ID of the other EPUB book.")

class ImageMatch(BaseModel):
    model_config = ConfigDict(frozen=True)

    image_name: str = Field(description="Name of the image within this book.")
    confidence: float = Field(description="Confidence of the match (closeness of images).")
    other_image_id: int = Field(description="ID of the image this one matched with.")

class ContentMatch(BaseModel):
    model_config = ConfigDict(frozen=True)

    confidence: float = Field(description="Confidence of the match (similarity of content).")
    other_book_id: int = Field(description="ID of the other book.")
