from api.speechgen import SpeechGenService
from common_lib.test import time_it

speechgen = SpeechGenService(None)

test_text = "I nearly shuddered at the idea of drinking the wrong one. “It’s Pantalain’s cup,” I said, rounding the table to pick it up. It detached easily from the table, even though it had grown up out of its surface. I confirmed the choice with Tumble, then tipped it back. Here goes nothing."

@time_it
def test_test3():
    result = speechgen.phonemize(test_text)
    print(test_text)
    print(result)
