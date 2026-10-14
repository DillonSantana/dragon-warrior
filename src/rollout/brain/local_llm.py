"""A minimal client for a local Ollama server."""

import json
import urllib.error
import urllib.request

SYSTEM_PROMPT = (
    "You are RollOut, a calm, steady voice assistant running on Dillon's Mac. "
    "Your replies are spoken aloud, so answer in one to three short sentences of plain speech: "
    "no lists, markdown, emoji or code. If you don't know something, say so briefly."
)


class OllamaError(RuntimeError):
    pass


class LocalLLM:
    def __init__(self, model: str, url: str, history_turns: int = 6, timeout: float = 120):
        self.model = model
        self.url = url.rstrip("/")
        self.history_turns = history_turns
        self.timeout = timeout
        self.history: list[dict[str, str]] = []

    def ask(self, prompt: str) -> str:
        messages = [{"role": "system", "content": SYSTEM_PROMPT}, *self.history]
        messages.append({"role": "user", "content": prompt})
        reply = self._chat(messages)
        self.history += [
            {"role": "user", "content": prompt},
            {"role": "assistant", "content": reply},
        ]
        self.history = self.history[-2 * self.history_turns :]
        return reply

    def _chat(self, messages: list[dict[str, str]]) -> str:
        body = json.dumps(
            {"model": self.model, "messages": messages, "stream": False, "think": False}
        ).encode()
        request = urllib.request.Request(
            f"{self.url}/api/chat", data=body, headers={"Content-Type": "application/json"}
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                data = json.load(response)
        except urllib.error.URLError as exc:
            raise OllamaError(f"Can't reach Ollama at {self.url}: {exc}") from exc
        return data["message"]["content"].strip()
