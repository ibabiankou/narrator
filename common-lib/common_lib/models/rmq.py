import uuid

from common_lib.rmq import RMQMessage


class PhonemizeText(RMQMessage):
    type = "phonemize"
    book_id: uuid.UUID
    section_id: int
    track_id: int
    text: str

    voice: str = "am_adam"

class PhonemesResponse(RMQMessage):
    type = "phonemes"
    book_id: uuid.UUID
    section_id: int
    track_id: int
    phonemes: str

    voice: str

class SynthesizeSpeech(RMQMessage):
    type = "synthesize"
    book_id: uuid.UUID
    section_id: int
    track_id: int
    phonemes: str
    # Path to a directory where the speech file should be uploaded.
    file_path: str

    voice: str = "am_adam"
    speed: float = 1

class SpeechResponse(RMQMessage):
    type = "speech"
    book_id: uuid.UUID
    section_id: int
    track_id: int
    # Path to the speech file generated.
    file_path: str
    duration: float
    bytes: int
