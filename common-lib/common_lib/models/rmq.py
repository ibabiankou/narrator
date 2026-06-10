import uuid
from datetime import datetime

from common_lib.models.tts import FragmentGroups
from common_lib.rmq import RMQMessage


class NarrateRequest(RMQMessage):
    type = "narrate"

    queue_id: int
    book_id: uuid.UUID
    tts_model: str
    voice: str
    track_base_name: str
    order: int
    fragments: FragmentGroups


class NarrateResponse(RMQMessage):
    type = "narrate"

    queue_id: int
    narration_time_s: float
    completed: datetime
    duration_s: float
    size_bytes: int
