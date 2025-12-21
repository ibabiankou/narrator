from common_lib.rmq import RMQMessage


class PhonemizeText(RMQMessage):
    type = "phonemize"
    section_id: int
    text: str


class PhonemesResponse(RMQMessage):
    type = "phonemes"
    section_id: int
    phonemes: str
