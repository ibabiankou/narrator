from pydantic import BaseModel


class PhonemizeText(BaseModel):
    section_id: int
    text: str
