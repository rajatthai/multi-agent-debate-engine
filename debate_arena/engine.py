import json
import os
from dataclasses import dataclass
from typing import Dict, List

import requests
from dotenv import load_dotenv

from .personas import get_persona_profile

load_dotenv()


@dataclass
class DebateConfig:
    rounds: int = 3
    word_limit: int = 100
    judge_limit: int = 150
    topic_domain: str = "General"


class DebateEngine:
    def __init__(self, api_key: str, api_url: str, model_for: str, model_against: str, model_judge: str, config: DebateConfig):
        self.api_key = api_key
        self.api_url = api_url
        self.model_for = model_for
        self.model_against = model_against
        self.model_judge = model_judge
        self.config = config

    @classmethod
    def from_env(cls, config: DebateConfig):
        return cls(
            api_key=os.getenv("OPENROUTER_API_KEY", ""),
            api_url=os.getenv("OPENROUTER_API_URL", "https://openrouter.ai/api/v1/chat/completions"),
            model_for=os.getenv("OPENROUTER_MODEL_DEBATER_1", "nvidia/nemotron-3-nano-30b-a3b:free"),
            model_against=os.getenv("OPENROUTER_MODEL_DEBATER_2", "nvidia/nemotron-3-super-120b-a12b:free"),
            model_judge=os.getenv("OPENROUTER_MODEL_JUDGE", "moonshotai/kimi-k2.6:free"),
            config=config,
        )

    def _headers(self):
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def _stream_chat(self, model: str, system_prompt: str, user_prompt: str):
        payload = {
            "model": model,
            "stream": True,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
        resp = requests.post(
            self.api_url,
            headers=self._headers(),
            json=payload,
            stream=True,
            timeout=120,
        )
        resp.raise_for_status()

        # Force UTF-8 decoding at the source to avoid mojibake characters in the output
        for raw_line in resp.iter_lines(decode_unicode=False):
            if not raw_line:
                continue
            line = raw_line.decode("utf-8")   # explicit UTF-8, no guessing
            if not line.startswith("data: "):
                continue
            data = line[6:]
            if data.strip() == "[DONE]":
                break
            try:
                obj = json.loads(data)
                delta = obj.get("choices", [{}])[0].get("delta", {}).get("content")
                if delta:
                    yield delta
            except json.JSONDecodeError:
                continue

    def _nonstream_text(self, model: str, system_prompt: str, user_prompt: str) -> str:
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
        resp = requests.post(
            self.api_url,
            headers=self._headers(),
            json=payload,
            timeout=120,
        )
        resp.raise_for_status()
        resp.encoding = "utf-8"   # force UTF-8 before .json() parses it
        data = resp.json()
        return data["choices"][0]["message"]["content"].strip()

    def _speaker_prompt(self, speaker: str, side: str) -> str:
        profile = get_persona_profile(speaker)
        expertise = ", ".join(profile.get("expertise", [])) or "general reasoning"
        style = profile.get("style", "balanced")
        return f"""
        You are {speaker}, arguing {side} in a debate.
        Selected domain: {self.config.topic_domain}.
        Expertise: {expertise}.
        Style: {style}.

        Rules:
        - Stay strictly within the selected domain.
        - Do not mention your own name in the argument.
        - Do not claim expertise outside your assigned domain.
        - Be concise, persuasive, and direct.
        - Keep the response under {self.config.word_limit} words.
        """.strip()

    def _judge_prompt(self, judge: str) -> str:
        profile = get_persona_profile(judge)
        expertise = ", ".join(profile.get("expertise", [])) or "balanced evaluation"
        style = profile.get("style", "balanced")
        return f"""
        You are {judge}, the judge of this debate.
        Selected domain: {self.config.topic_domain}.
        Expertise: {expertise}.
        Style: {style}.

        Rules:
        - Evaluate only within the selected domain.
        - Do not mention your own name.
        - Keep the verdict under {self.config.judge_limit} words.
        - Be balanced and decisive.
        """.strip()

    def generate_for_argument(self, topic: str, speaker: str):
        system_prompt = self._speaker_prompt(speaker, "FOR")
        user_prompt = f"""
        Topic domain: {self.config.topic_domain}
        Topic: {topic}

        Write a FOR argument for this topic.
        """.strip()
        return self._stream_chat(self.model_for, system_prompt, user_prompt)

    def generate_against_argument(self, topic: str, speaker: str, prior_argument: str):
        system_prompt = self._speaker_prompt(speaker, "AGAINST")
        user_prompt = f"""
        Topic domain: {self.config.topic_domain}
        Topic: {topic}

        Opponent argument:
        {prior_argument}

        Write a strong AGAINST response.
        """.strip()
        return self._stream_chat(self.model_against, system_prompt, user_prompt)

    def generate_verdict(self, topic: str, judge: str, transcript: List[Dict[str, str]]):
        system_prompt = self._judge_prompt(judge)
        debate_text = "\n\n".join(
            f"{item['speaker']} ({item['side']}): {item['text']}" for item in transcript
        )
        user_prompt = f"""
        Topic domain: {self.config.topic_domain}
        Topic: {topic}

        Debate transcript:
        {debate_text}

        Deliver the verdict. Clearly name which side was stronger and why.
        """.strip()
        return self._stream_chat(self.model_judge, system_prompt, user_prompt)
    
    def generate_topic(self, topic_domain: str, p1: str, p2: str) -> str:
        profile1 = get_persona_profile(p1)
        profile2 = get_persona_profile(p2)

        system_prompt = f"""
        You generate short, interesting debate topics.
        Domain: {topic_domain}.
        Keep it under 50 words.
        Make it suitable for both selected debaters.
        Return only the topic text.
        """.strip()

        user_prompt = f"""
        Generate one debate topic under 50 words for a debate between:
        - {p1} ({profile1.get('style', 'balanced')})
        - {p2} ({profile2.get('style', 'balanced')})

        Return only the topic text.
        """.strip()

        return self._nonstream_text(self.model_for, system_prompt, user_prompt)
