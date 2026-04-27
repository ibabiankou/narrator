from typing import Optional

from pydantic import BaseModel, ConfigDict


class Reference(BaseModel):
    model_config = ConfigDict(
        extra='allow',
    )
    key: str


class Link(BaseModel):
    model_config = ConfigDict(
        extra='allow',
    )
    url: str
    title: str


class Author(BaseModel):
    model_config = ConfigDict(
        extra='allow',
    )

    key: str
    name: str
    alternate_names: Optional[list[str]] = None

    fuller_name: Optional[str] = None
    personal_name: Optional[str] = None
    title: Optional[str] = None
    links: Optional[list[Link]] = None


class Edition(BaseModel):
    model_config = ConfigDict(
        extra='allow',
    )

    key: str
    title: str

    series: Optional[list[str]] = None
    description: Optional[str] = None

    covers: Optional[list[int]] = None
    authors: Optional[list[Reference]] = None
    isbn_10: Optional[list[str]] = None
    isbn_13: Optional[list[str]] = None
