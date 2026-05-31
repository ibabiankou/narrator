from typing import Optional, List

from pydantic import BaseModel


class TocItem(BaseModel):
    href: str
    title: Optional[str]

class TableOfContent(BaseModel):
    items: List[TocItem]
