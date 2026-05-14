from typing import List, Optional

from pydantic import BaseModel, Field, ConfigDict


class Title(BaseModel):
    model_config = ConfigDict(frozen=True)

    title: str = Field(description="Name given to a resource.")
    subtitles: Optional[List[str]] = Field(
        description="Word, character, or group of words and/or characters that contains the remainder of the title after the main title. Possible title component.",
        default=None)
    part_number: Optional[int] = Field(description="Part or section enumeration of a title. Possible title component.",
                                       default=None)
    part_name: Optional[int] = Field(description="Part or section name of a title. Possible title component.",
                                     default=None)

class Identifier(BaseModel):
    model_config = ConfigDict(frozen=True)
    type: str = Field(description="Type of ID, e.g. isbn, uuid, asin etc.")
    value: str = Field(description="The identifier.")

class AssetRef(BaseModel):
    model_config = ConfigDict(frozen=True)

    asset_id: int = Field(description="ID of the referenced asset.")
    url: Optional[str] = Field(description="URL the asset can be accessed at.")
