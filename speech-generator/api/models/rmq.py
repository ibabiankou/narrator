from pydantic import BaseModel


class PhonemizeText(BaseModel):
    section_id: int
    text: str

class PhonemesResponse(BaseModel):
    section_id: int
    phonemes: str
