import pytest

from app.services.chunking import chunk_pages, split_sentences


def test_empty_input_gives_no_chunks():
    assert chunk_pages([]) == []
    assert chunk_pages(["", "   \n  "]) == []


def test_sentences_ignore_hard_line_breaks():
    text = "This sentence is\nbroken over two lines. Here is another one!\n\nNew paragraph."
    assert split_sentences(text) == [
        "This sentence is broken over two lines.",
        "Here is another one!",
        "New paragraph.",
    ]


def test_chunks_respect_the_size_limit():
    pages = [" ".join(f"Sentence number {i} is here." for i in range(200))]
    chunks = chunk_pages(pages, size=200, overlap=40)
    assert len(chunks) > 5
    assert all(len(chunk.text) <= 200 for chunk in chunks)


def test_consecutive_chunks_overlap():
    pages = [" ".join(f"Sentence number {i} is here." for i in range(50))]
    chunks = chunk_pages(pages, size=200, overlap=70)
    first_end = chunks[0].text.split(". ")[-1]
    assert first_end.rstrip(".") in chunks[1].text


def test_page_range_is_tracked_across_pages():
    pages = ["Alpha is on page one.", "Beta is on page two.", "Gamma is on page three."]
    chunks = chunk_pages(pages, size=1000, overlap=100)
    assert len(chunks) == 1
    assert (chunks[0].page_start, chunks[0].page_end) == (1, 3)


def test_each_chunk_points_to_the_right_page():
    pages = ["A" * 50 + ".", "B" * 50 + "."]
    chunks = chunk_pages(pages, size=60, overlap=10)
    assert [(c.page_start, c.page_end) for c in chunks] == [(1, 1), (2, 2)]


def test_very_long_sentence_is_split_on_words():
    pages = [" ".join(["word"] * 500)]
    chunks = chunk_pages(pages, size=100, overlap=10)
    assert len(chunks) > 10
    assert all(len(chunk.text) <= 100 for chunk in chunks)


def test_invalid_settings_are_rejected():
    with pytest.raises(ValueError):
        chunk_pages(["text"], size=100, overlap=100)
    with pytest.raises(ValueError):
        chunk_pages(["text"], size=0, overlap=0)
