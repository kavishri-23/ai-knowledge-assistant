from app.services.bm25 import BM25, tokenize


def test_tokenize_lowercases_and_drops_stopwords():
    assert tokenize("What is the Capital of France?") == ["capital", "france"]


def test_rare_matching_word_wins():
    docs = [
        tokenize("The cat sat on the mat"),
        tokenize("Invoice 4821 is overdue"),
        tokenize("The weather is nice today"),
    ]
    index = BM25(docs)
    assert index.top(tokenize("invoice 4821"), 3) == [1]


def test_no_match_returns_nothing():
    index = BM25([tokenize("apples and oranges")])
    assert index.top(tokenize("zebra"), 5) == []


def test_empty_index_is_safe():
    index = BM25([])
    assert index.top(["anything"], 3) == []
