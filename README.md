# 🎭 LLM Debate Arena

> Multi-agent AI debates between historical personas, powered by free LLMs via [OpenRouter](https://openrouter.ai).

🔗 **[Live Demo →](YOUR_STREAMLIT_URL_HERE)**

---

## What it does

- **Two debaters** argue FOR and AGAINST a topic in configurable rounds.
- **One judge** evaluates and delivers a verdict.
- **Persona presets** — philosophers, economists, scientists, and more.
- **Sticky topic banner** so the debate context is always visible.
- **Chat-style transcript** — one debater on the left, one on the right.
- **Sample mode** for instant testing — no API key needed.
- **JSON export** to download the full debate transcript.

---

## Tech stack

| Layer | Tool |
|---|---|
| Frontend | Streamlit |
| LLM backend | OpenRouter (free-tier models) |
| HTTP | Requests |
| Config | python-dotenv |

---

## Quickstart

```bash
git clone https://github.com/YOUR_USERNAME/llm-debate-arena
cd llm-debate-arena
pip install -r requirements.txt
cp .env.example .env          # then add your OpenRouter key
streamlit run app.py
```

Try **Sample mode** first — no API key needed.

---

## Streamlit Cloud deploy

1. Push this repo to GitHub.
2. Go to [share.streamlit.io](https://share.streamlit.io) and create a new app.
3. Select `app.py` as the entrypoint.
4. Add secrets in the Streamlit dashboard:

```toml
OPENROUTER_API_KEY = "your_key_here"
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_MODEL_DEBATER_1 = "nvidia/nemotron-3-nano-30b-a3b:free"
OPENROUTER_MODEL_DEBATER_2 = "nvidia/nemotron-3-super-120b-a12b:free"
OPENROUTER_MODEL_JUDGE = "moonshotai/kimi-k2.6:free"
```

5. Deploy and share the public URL.

---

## Architecture

```
topic + personas
      │
      ▼
 DebateEngine.run()
      │
      ├─► Model 1 (FOR)  ──► argument
      │
      ├─► Model 2 (AGAINST) ──► counter-argument
      │        ↑ (repeated per round)
      │
      └─► Judge model ──► verdict
              │
              ▼
         Streamlit UI
         (chat bubbles + sticky topic + JSON export)
```

---

## Security

- Never commit `.env`.
- Only `.env.example` (with placeholder values) is tracked in Git.
- Use Streamlit secrets for deployed credentials.

---

## GitHub Topics

Add these to your repo: `llm` · `multi-agent` · `openrouter` · `streamlit` · `python` · `debate` · `ai` · `nlp`
