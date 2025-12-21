from common_lib.rmq import RMQMessage


class PhonemizeText(RMQMessage):
    type = "phonemize"
    section_id: int
    track_id: int
    text: str


class PhonemesResponse(RMQMessage):
    type = "phonemes"
    section_id: int
    track_id: int
    phonemes: str

class SynthesizeSpeech(RMQMessage):
    type = "synthesize"
    track_id: int
    phonemes: str
    file_path: str

class SpeechResponse(RMQMessage):
    type = "speech"
    track_id: int
    file_path: str
    duration: float
