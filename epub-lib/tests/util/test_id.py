from epub_lib.util.id import normalize_identifier


class TestIds:
    def test_id_normalization(self):
        cases = [
            ("urn:isbn:978-1-4976-7282-6", ("isbn", "9781497672826")),
            ("isbn:978-1-4976-7282-6", ("isbn", "9781497672826")),
            ("1-497-67282-1", ("isbn", "9781497672826")),
            ("b08kgt4clq", ("asin", "B08KGT4CLQ")),
            ("asin:b08kgt4clq", ("asin", "B08KGT4CLQ")),
            ("urn:asin:b08kgt4clq", ("asin", "B08KGT4CLQ")),
            ("urn:uuid:46e16d39-febb-4c7a-93a8-08791609fe95", ("uuid", "46e16d39-febb-4c7a-93a8-08791609fe95")),
            ("uuid:46e16d39-febb-4c7a-93a8-08791609fe95", ("uuid", "46e16d39-febb-4c7a-93a8-08791609fe95")),
            ("46e16d39-febb-4c7a-93a8-08791609fe95", ("uuid", "46e16d39-febb-4c7a-93a8-08791609fe95")),
            ("calibre:2943", ("calibre", "2943")),
            ("goodreads:57964597", ("goodreads", "57964597")),
            ("comb16346", ("unknown", "comb16346")),
            ("16b28f1a74309fc7472e0a3917a13234", ("uuid", "16b28f1a-7430-9fc7-472e-0a3917a13234")),
            ("38c7b58c4e0911f1bcd6325096b39f47", ("uuid", "38c7b58c-4e09-11f1-bcd6-325096b39f47")),
            ("000003e84e0921f19b00325096b39f47", ("uuid", "000003e8-4e09-21f1-9b00-325096b39f47")),
            ("a6065d2f4d8437b4904eb15a8a001945", ("uuid", "a6065d2f-4d84-37b4-904e-b15a8a001945")),
            ("187d7cf339394a63bd491358f57783ff", ("uuid", "187d7cf3-3939-4a63-bd49-1358f57783ff")),
            ("10fd9636f18455f38b7488b9e21b9476", ("uuid", "10fd9636-f184-55f3-8b74-88b9e21b9476")),
            ("0809230410", ("isbn", "9780809230419")),
            ("a9781784780340", ("isbn", "9781784780340")),
            ("ISBN-978-0-231-16347-7", ("isbn", "9780231163477")),
            ("eISBN-978-0-231-53803-9", ("isbn", "9780231538039")),
        ]

        for input, expected in cases:
            actual = normalize_identifier(input)
            assert actual[0] == expected[0]
            assert actual[1] == expected[1]
