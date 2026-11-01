"""Errors whose messages are safe to show to the user."""


class IngestError(Exception):
    """A document could not be processed."""


class LLMError(Exception):
    """The language model could not be reached or returned something unusable."""
