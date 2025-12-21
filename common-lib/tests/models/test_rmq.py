from common_lib.rmq import RMQMessage


class DummyMessage(RMQMessage):
    type = "test_type"

    prop: str

def test_rmq_message_serialization():
    msg = DummyMessage(prop="test value")
    json_str = msg.model_dump_json()
    assert json_str == '{"prop":"test value"}'
    assert msg.type == "test_type"

def test_rmq_message_deserialization():
    msg = DummyMessage.model_validate_json('{"prop":"test value"}')
    assert msg.type == "test_type"
    assert msg.prop == "test value"

def test_rmq_message_deserialization_type_override():
    msg = DummyMessage.model_validate_json('{"prop":"used","type":"should_be_ignored"}')
    assert msg.prop == "used"
    assert msg.type == "test_type"
