"""Split page text into overlapping, sentence-aware chunks that remember their pages."""

import re
from collections.abc import Iterator
from dataclasses import dataclass

_SENTENCE_BREAK = re.compile(r"(?<=[.!?])\s+|\n\s*\n")
_WHITESPACE = re.compile(r"\s+")


@dataclass(frozen=True)
class Chunk:
    text: str
    page_start: int
    page_end: int


def split_sentences(text: str) -> list[str]:
    """Split on sentence ends and blank lines; single line breaks become spaces."""
    parts = _SENTENCE_BREAK.split(text.replace("\r", ""))
    cleaned = (_WHITESPACE.sub(" ", part).strip() for part in parts)
    return [part for part in cleaned if part]


def _hard_split(sentence: str, size: int) -> list[str]:
    """Break a very long 'sentence' at word boundaries so no piece exceeds `size`."""
    pieces: list[str] = []
    current = ""
    for word in sentence.split(" "):
        if current and len(current) + 1 + len(word) > size:
            pieces.append(current)
            current = word
        else:
            current = f"{current} {word}" if current else word
    if current:
        pieces.append(current)
    return pieces


def _units(pages: list[str], size: int) -> Iterator[tuple[str, int]]:
    """Yield (sentence, page_number) for the whole document, in reading order."""
    for page_number, text in enumerate(pages, start=1):
        for sentence in split_sentences(text):
            pieces = _hard_split(sentence, size) if len(sentence) > size else [sentence]
            for piece in pieces:
                yield piece, page_number


def _joined_length(units: list[tuple[str, int]]) -> int:
    return sum(len(text) for text, _ in units) + max(len(units) - 1, 0)


def _carry_over(units: list[tuple[str, int]], overlap: int) -> list[tuple[str, int]]:
    """Take the last few sentences (up to `overlap` characters) to start the next chunk."""
    carried: list[tuple[str, int]] = []
    total = 0
    for unit in reversed(units):
        total += len(unit[0]) + (1 if carried else 0)
        if total > overlap:
            break
        carried.insert(0, unit)
    return carried


def chunk_pages(pages: list[str], size: int = 800, overlap: int = 150) -> list[Chunk]:
    """Group sentences into chunks of at most `size` characters.

    Consecutive chunks share about `overlap` characters, and the overlap may cross a
    page boundary, so an answer that spans two pages is not cut in half.
    """
    if size <= 0 or overlap < 0 or overlap >= size:
        raise ValueError("chunk settings must satisfy 0 <= overlap < size")

    chunks: list[Chunk] = []
    current: list[tuple[str, int]] = []
    current_length = 0

    def flush() -> None:
        text = " ".join(part for part, _ in current)
        chunks.append(Chunk(text, current[0][1], current[-1][1]))

    for text, page in _units(pages, size):
        extra = len(text) + (1 if current else 0)
        if current and current_length + extra > size:
            flush()
            current = _carry_over(current, overlap)
            if current and _joined_length(current) + 1 + len(text) > size:
                current = []
            current_length = _joined_length(current)
            extra = len(text) + (1 if current else 0)
        current.append((text, page))
        current_length += extra

    if current:
        flush()
    return chunks
