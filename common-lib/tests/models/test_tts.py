from common_lib.models.tts import Token


class TestTTS:

    def test_starts_with_whitespace(self):
        positive_cases = [" ", " word", "\nword", "\tword"]
        for text in positive_cases:
            t = Token(text)
            assert t.starts_with_whitespace()

        negative_cases = ["", "word"]
        for text in negative_cases:
            t = Token(text)
            assert not t.starts_with_whitespace()

    def test_ends_with_whitespace(self):
        positive_cases = [" ", "word ", "word\n", "word\t"]
        for text in positive_cases:
            t = Token(text)
            assert t.ends_with_whitespace()

        negative_cases = ["", "word"]
        for text in negative_cases:
            t = Token(text)
            assert not t.ends_with_whitespace()
