"""A small client for a local Ollama server."""

import json
from collections.abc import Iterator

import httpx

from app.services.errors import LLMError


class OllamaClient:
    def __init__(self, base_url: str, model: str, timeout: float):
        self._base = base_url.rstrip("/")
        self._model = model
        self._timeout = timeout

    @property
    def model(self) -> str:
        return self._model

    def _payload(self, prompt: str, stream: bool) -> dict:
        return {"model": self._model, "prompt": prompt, "stream": stream}

    def _explain(self, error: Exception) -> str:
        if isinstance(error, httpx.ConnectError):
            return f"Could not connect to Ollama at {self._base}. Is it running?"
        if isinstance(error, httpx.TimeoutException):
            return "The language model took too long to answer. Try a shorter question."
        if isinstance(error, httpx.HTTPStatusError) and error.response.status_code == 404:
            return f"Model '{self._model}' is not available. Run: ollama pull {self._model}"
        return "The language model returned an error."

    def ping(self) -> bool:
        try:
            return httpx.get(f"{self._base}/api/tags", timeout=2.0).status_code == 200
        except httpx.HTTPError:
            return False

    def generate(self, prompt: str) -> str:
        try:
            response = httpx.post(
                f"{self._base}/api/generate",
                json=self._payload(prompt, stream=False),
                timeout=self._timeout,
            )
            response.raise_for_status()
            answer = response.json().get("response", "").strip()
        except (httpx.HTTPError, ValueError) as error:
            raise LLMError(self._explain(error)) from error
        if not answer:
            raise LLMError("The language model returned an empty answer.")
        return answer

    def stream(self, prompt: str) -> Iterator[str]:
        """Yield the answer piece by piece as the model produces it."""
        try:
            with httpx.stream(
                "POST",
                f"{self._base}/api/generate",
                json=self._payload(prompt, stream=True),
                timeout=self._timeout,
            ) as response:
                response.raise_for_status()
                for line in response.iter_lines():
                    if not line:
                        continue
                    data = json.loads(line)
                    if data.get("response"):
                        yield data["response"]
                    if data.get("done"):
                        return
        except (httpx.HTTPError, ValueError) as error:
            raise LLMError(self._explain(error)) from error
