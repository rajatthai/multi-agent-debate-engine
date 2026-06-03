from dataclasses import dataclass
import json
import os
import time
import requests
from dotenv import load_dotenv
from typing import Iterator

@dataclass
class DebateConfig:
    rounds: int = 3
    word_limit: int = 100
    judge_limit: int = 150
    retry_delay: int = 2
    rate_limit_delay: float = 1.0
    max_retries: int = 3

class DebateEngine:
    def __init__(self, api_key, api_url, model_1, model_2, model_judge, cfg: DebateConfig):
        self.api_key = api_key
        self.api_url = api_url
        self.model_1 = model_1
        self.model_2 = model_2
        self.model_judge = model_judge
        self.cfg = cfg
        self.last_request = 0.0

    @classmethod
    def from_env(cls, cfg: DebateConfig):
        load_dotenv()
        return cls(
            api_key=os.getenv("OPENROUTER_API_KEY", ""),
            api_url=os.getenv("OPENROUTER_API_URL", "https://openrouter.ai/api/v1/chat/completions"),
            model_1=os.getenv("OPENROUTER_MODEL_DEBATER_1", "nvidia/nemotron-3-nano-30b-a3b:free"),
            model_2=os.getenv("OPENROUTER_MODEL_DEBATER_2", "nvidia/nemotron-3-super-120b-a12b:free"),
            model_judge=os.getenv("OPENROUTER_MODEL_JUDGE", "moonshotai/kimi-k2.6:free"),
            cfg=cfg,
        )

    def _rate_limit(self):
        elapsed = time.time() - self.last_request
        if elapsed < self.cfg.rate_limit_delay:
            time.sleep(self.cfg.rate_limit_delay - elapsed)

    def _stream(self, model: str, prompt: str) -> Iterator[str]:
        """Stream tokens from OpenRouter via SSE. Yields string chunks."""
        self._rate_limit()
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "text/event-stream",
        }
        payload = {
            "model": model,
            "stream": True,
            "messages": [{"role": "user", "content": prompt}],
        }
        for attempt in range(self.cfg.max_retries + 1):
            try:
                with requests.post(
                    self.api_url, headers=headers, json=payload,
                    stream=True, timeout=60
                ) as r:
                    self.last_request = time.time()
                    if r.status_code != 200:
                        time.sleep(self.cfg.retry_delay * (attempt + 1))
                        continue
                    for raw_line in r.iter_lines():
                        if not raw_line:
                            continue
                        line = raw_line.decode("utf-8")
                        if line.startswith(":"):
                            # SSE comment — keepalive, skip
                            continue
                        if line.startswith("data: "):
                            data = line[len("data: "):]
                            if data.strip() == "[DONE]":
                                return
                            try:
                                chunk = json.loads(data)
                                delta = chunk["choices"][0]["delta"].get("content", "")
                                if delta:
                                    yield delta
                            except (json.JSONDecodeError, KeyError, IndexError):
                                continue
                    return
            except requests.RequestException:
                time.sleep(self.cfg.retry_delay * (attempt + 1))

    def _collect(self, model: str, prompt: str) -> str:
        """Collect full text from a streaming call (non-UI path)."""
        return "".join(self._stream(model, prompt))

    def generate_for_argument(self, topic: str, p1: str) -> Iterator[str]:
        prompt = (
            f"You are {p1}. Do not mention your own name anywhere in your response.\n\n"
            f"Debate topic: {topic}\n"
            f"You are arguing FOR this topic. Write a concise argument in under {self.cfg.word_limit} words."
        )
        return self._stream(self.model_1, prompt)

    def generate_against_argument(self, topic: str, p2: str, previous: str) -> Iterator[str]:
        prompt = (
            f"You are {p2}. Do not mention your own name anywhere in your response.\n\n"
            f"Debate topic: {topic}\n"
            f"You are arguing AGAINST. The FOR argument was:\n{previous}\n\n"
            f"Write a concise counter-argument in under {self.cfg.word_limit} words."
        )
        return self._stream(self.model_2, prompt)

    def generate_verdict(self, topic: str, pj: str, transcript: list) -> Iterator[str]:
        prompt = (
            f"You are {pj}. Do not mention your own name anywhere in your response.\n\n"
            f"Debate topic: {topic}\n\nTranscript:\n{json.dumps(transcript, indent=2)}\n\n"
            f"Judge the debate in under {self.cfg.judge_limit} words. "
            f"State which side was more convincing and why."
        )
        return self._stream(self.model_judge, prompt)
