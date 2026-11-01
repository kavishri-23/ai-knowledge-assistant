from app.services.chunking import Chunk
from app.services.prompting import (
    NOT_FOUND,
    build_prompt,
    extract_citations,
    is_not_found,
)
from app.services.retrieval import Retriever, reciprocal_rank_fusion
from tests.fakes import FakeEmbedder, FakeStore

CHUNKS = [
    Chunk("Photosynthesis converts light energy into chemical energy in chloroplasts.", 1, 1),
    Chunk("The Treaty of Paris was signed in 1783 and ended the American Revolutionary War.", 2, 2),
    Chunk("Invoice 4821 totals 1250 dollars and is due on the first of March.", 3, 3),
]


def make_retriever(min_similarity=0.3):
    store, embedder = FakeStore(), FakeEmbedder()
    store.add("doc", "notes.pdf", CHUNKS, embedder.encode([c.text for c in CHUNKS]))
    retriever = Retriever(
        store, embedder, top_k=3, candidate_pool=10, min_similarity=min_similarity
    )
    return retriever


def test_fusion_rewards_agreement_between_rankings():
    scores = reciprocal_rank_fusion([["a", "b", "c"], ["b", "a", "d"]])
    assert scores["a"] == scores["b"] > scores["c"]
    assert set(scores) == {"a", "b", "c", "d"}


def test_hybrid_finds_the_matching_page_first():
    results = make_retriever().retrieve("doc", "What ended the American Revolutionary War?")
    assert results
    assert results[0].page_start == 2


def test_keyword_mode_finds_exact_identifiers():
    results = make_retriever().retrieve("doc", "invoice 4821 total", mode="keyword")
    assert results[0].page_start == 3


def test_unrelated_question_returns_nothing():
    assert make_retriever().retrieve("doc", "zzzz qqqq xxxx") == []


def test_unknown_document_returns_nothing():
    assert make_retriever().retrieve("missing", "photosynthesis") == []


def test_similarity_threshold_filters_weak_matches():
    strict = make_retriever(min_similarity=0.99)
    assert strict.retrieve("doc", "What ended the American Revolutionary War?") == []


def test_prompt_numbers_sources_and_neutralises_markup():
    retriever = make_retriever()
    chunks = retriever.retrieve("doc", "Treaty of Paris")
    prompt = build_prompt("Who signed it?", chunks)
    assert '<source id="1" pages="2">' in prompt
    assert "Question: Who signed it?" in prompt
    assert NOT_FOUND in prompt


def test_citation_parsing_ignores_unknown_numbers():
    assert extract_citations("Yes [1], also [3] and [9] and [1].", 3) == [1, 3]
    assert extract_citations("No citations here.", 3) == []


def test_not_found_detection():
    assert is_not_found(NOT_FOUND)
    assert is_not_found("Sorry, I could not find this information in the document")
    assert not is_not_found("The treaty was signed in 1783 [1].")
