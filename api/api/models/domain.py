from typing import Optional, List

from pydantic import BaseModel, Field


class BookMetadata(BaseModel):
    cover: Optional[str] = Field(default=None, description="The cover image of the book.")
    title: Optional[str] = Field(default=None, description="The full title of the book.")
    series: Optional[str] = Field(default=None, description="The name of the series.")
    description: Optional[str] = Field(default=None, description="A short description of the book.")

    authors: List[str] = Field(default=[], description="A list of authors of the book.")
    isbns: List[str] = Field(default=[], description="The 10 or 13-digit ISBN(s) if found in the text.")


class MetadataCandidate(BookMetadata):
    source: str = Field(description="The source of this metadata candidate.")


class MetadataCandidates(BaseModel):
    candidates: list[MetadataCandidate]
    preferred_index: int = Field(default=0, description="Zero based index of the candidate we think to be the best.")
    selected_index: Optional[str] = Field(default=None, description="Zero based index of the candidate selected by the user.")
