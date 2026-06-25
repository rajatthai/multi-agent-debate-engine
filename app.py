import json
import time
import uuid
import queue
import threading
import random
import streamlit as st
from debate_arena.engine import DebateEngine, DebateConfig
from debate_arena.models import (
    default_model_ids,
    fetch_free_text_models,
    model_name_map,
    resolve_default_index,
)
from debate_arena.personas import PERSONA_GROUPS, get_personas_for_group

TOPIC_BANK = {
    "Philosophy": [
        "Can moral responsibility survive if human decisions are increasingly delegated to machines?",
        "Is truth more important than social harmony in public discourse?",
    ],
    "Politics": [
        "Is strong executive leadership more effective than broad consensus in a crisis?",
        "Should social media platforms have stricter rules for political speech?",
    ],
    "Economics": [
        "Should governments prioritize growth or inequality reduction during downturns?",
        "Is free-market competition enough to drive innovation without regulation?",
    ],
    "Technology": [
        "Should AI systems be allowed to make high-stakes decisions without human oversight?",
        "Is open-source software better than proprietary software for long-term innovation?",
    ],
    "Science": [
        "Should scientific research prioritize practical impact over theoretical discovery?",
        "Is it ever acceptable to slow innovation in science for safety reasons?",
    ],
}


st.set_page_config(page_title="LLM Debate Arena", page_icon="🎭", layout="wide")

DEFAULT_HINT_INTERVAL = 4.0

st.markdown("""
<style>
  html { scroll-behavior: smooth; }
  .stApp {
    background:
      radial-gradient(circle at top left, rgba(15,118,110,0.08), transparent 22%),
      radial-gradient(circle at top right, rgba(29,78,216,0.06), transparent 20%),
      linear-gradient(180deg, #f8fafc 0%, #eef4f7 100%);
  }
  @media (prefers-color-scheme: dark) {
    .stApp {
      background:
        radial-gradient(circle at top left, rgba(15,118,110,0.10), transparent 24%),
        radial-gradient(circle at top right, rgba(59,130,246,0.10), transparent 20%),
        linear-gradient(180deg, #0b1220 0%, #0f172a 100%);
    }
  }
  [data-testid="stAppViewContainer"] { scroll-behavior: smooth; }
  .block-container { padding-top: 1.25rem; padding-bottom: 2rem; max-width: 1180px; }
  .topic-banner {
    position: sticky; top: 0.5rem; z-index: 999;
    background: linear-gradient(135deg, #0f766e 0%, #115e59 100%);
    color: #fff; padding: 0.95rem 1.15rem; border-radius: 1rem;
    font-size: 1.02rem; font-weight: 700; margin: 0.35rem 0 1rem 0;
    box-shadow: 0 10px 28px rgba(15,118,110,0.28);
    word-break: break-word; border: 1px solid rgba(255,255,255,0.18);
  }
  .chat-shell {
    border: 1px solid rgba(148,163,184,0.16);
    background: rgba(255,255,255,0.62);
    backdrop-filter: blur(12px); -webkit-backdrop-filter: blur(12px);
    border-radius: 1.5rem; padding: 1.1rem;
    box-shadow: 0 20px 50px rgba(15,23,42,0.08);
  }
  @media (prefers-color-scheme: dark) {
    .chat-shell {
      background: rgba(15,23,42,0.62);
      border: 1px solid rgba(148,163,184,0.14);
      box-shadow: 0 20px 50px rgba(2,6,23,0.38);
    }
  }
  .msg-row {
    display: flex; align-items: flex-end; gap: 0.78rem;
    margin-bottom: 1rem; width: 100%; animation: fadeUp 220ms ease-out;
  }
  .msg-row.right { justify-content: flex-end; }
  .msg-row.left  { justify-content: flex-start; }
  .avatar {
    width: 40px; height: 40px; border-radius: 999px;
    display: flex; align-items: center; justify-content: center;
    font-weight: 800; font-size: 0.95rem; color: white; flex-shrink: 0;
    box-shadow: 0 8px 18px rgba(0,0,0,0.16); border: 1px solid rgba(255,255,255,0.18);
  }
  .avatar.left  { background: linear-gradient(135deg, #0f766e 0%, #0d9488 100%); }
  .avatar.right { background: linear-gradient(135deg, #1d4ed8 0%, #2563eb 100%); }
  .avatar.judge { background: linear-gradient(135deg, #a16207 0%, #ca8a04 100%); }
  .bubble-wrap { max-width: min(72%, 760px); }
  .bubble {
    border-radius: 1.15rem; padding: 0.92rem 1rem;
    box-shadow: 0 10px 30px rgba(15,23,42,0.08);
    line-height: 1.58; border: 1px solid rgba(148,163,184,0.18);
  }
  .bubble.left {
    background: linear-gradient(180deg, #ecfdf5 0%, #dcfce7 100%);
    color: #0f172a; border-bottom-left-radius: 0.35rem;
  }
  .bubble.right {
    background: linear-gradient(180deg, #eff6ff 0%, #dbeafe 100%);
    color: #0f172a; border-bottom-right-radius: 0.35rem;
  }
  .bubble.judge {
    background: linear-gradient(180deg, #fff8dc 0%, #fef3c7 100%);
    color: #422006; border-bottom-left-radius: 0.35rem;
  }
  @media (prefers-color-scheme: dark) {
    .bubble.left {
      background: linear-gradient(180deg, #14362f 0%, #102b25 100%);
      color: #f0fdf9; border-color: rgba(52,211,153,0.18); box-shadow: 0 10px 30px rgba(0,0,0,0.24);
    }
    .bubble.right {
      background: linear-gradient(180deg, #192944 0%, #142238 100%);
      color: #eff6ff; border-color: rgba(96,165,250,0.16); box-shadow: 0 10px 30px rgba(0,0,0,0.24);
    }
    .bubble.judge {
      background: linear-gradient(180deg, #47320c 0%, #34260d 100%);
      color: #fde68a; border-color: rgba(250,204,21,0.16); box-shadow: 0 10px 30px rgba(0,0,0,0.26);
    }
  }
  .bubble.typing { opacity: 0.96; font-style: italic; }
  .bubble.left.typing  { background: linear-gradient(180deg, #dff7eb 0%, #ccf2df 100%); color: #14532d; }
  .bubble.right.typing { background: linear-gradient(180deg, #dbeafe 0%, #cfddfb 100%); color: #1e3a8a; }
  .bubble.judge.typing { background: linear-gradient(180deg, #fef3c7 0%, #fde68a 100%); color: #713f12; }
  .label {
    font-size: 0.76rem; font-weight: 800; letter-spacing: 0.05em;
    text-transform: uppercase; margin-bottom: 0.35rem; color: #334155;
  }
  @media (prefers-color-scheme: dark) { .label { color: #cbd5e1; } }
  .verdict-box {
    background: linear-gradient(180deg, #fff7d6 0%, #ffefb3 100%);
    border: 1px solid rgba(202,138,4,0.35); border-radius: 1.2rem;
    padding: 1.1rem 1.15rem; margin-top: 1.4rem; color: #4b3a00;
    box-shadow: 0 16px 36px rgba(161,98,7,0.12);
  }
  .verdict-title { font-weight: 800; margin-bottom: 0.45rem; font-size: 0.98rem; }
  @media (prefers-color-scheme: dark) {
    .verdict-box {
      background: linear-gradient(180deg, #3d2c0b 0%, #2f230b 100%);
      border-color: rgba(250,204,21,0.26); color: #fde68a; box-shadow: 0 16px 36px rgba(0,0,0,0.24);
    }
  }
  .dots::after {
    content: ""; display: inline-block; width: 1.35em;
    animation: dots 1.2s steps(4, end) infinite; overflow: hidden; vertical-align: bottom;
  }
  @keyframes fadeUp {
    from { opacity: 0; transform: translateY(6px); }
    to   { opacity: 1; transform: translateY(0); }
  }
  .meta-chip {
    display: inline-flex; align-items: center; gap: 0.35rem; padding: 0.35rem 0.65rem;
    border-radius: 999px; background: rgba(255,255,255,0.72);
    border: 1px solid rgba(148,163,184,0.18); font-size: 0.8rem; color: #334155;
    margin-right: 0.45rem; margin-bottom: 0.45rem;
  }
  @media (prefers-color-scheme: dark) {
    .meta-chip {
      background: rgba(15,23,42,0.72); color: #cbd5e1; border-color: rgba(148,163,184,0.12);
    }
  }
            
  .rematch-banner {
    margin-top: 1rem;
    padding: 1rem 1.15rem;
    border-radius: 1.1rem;
    background: linear-gradient(180deg, rgba(255,247,214,0.96) 0%, rgba(255,239,179,0.96) 100%);
    border: 1px solid rgba(202,138,4,0.28);
    box-shadow: 0 14px 32px rgba(161,98,7,0.10);
    color: #4b3a00;
    font-weight: 700;
    text-align: center;
    line-height: 1.45;
  }

  @media (prefers-color-scheme: dark) {
    .rematch-banner {
      background: linear-gradient(180deg, rgba(61,44,11,0.96) 0%, rgba(47,35,11,0.96) 100%);
      border-color: rgba(250,204,21,0.22);
      box-shadow: 0 14px 32px rgba(0,0,0,0.24);
      color: #fde68a;
    }
  }

  .rematch-spacer {
    height: 0.85rem;
  }

  .bubble.verdict {
    background: linear-gradient(180deg, #fff7d6 0%, #ffefb3 100%);
    border: 1px solid rgba(202,138,4,0.35);
  }
               
  .model-chip {
  display: inline-flex;
  align-items: center;
  padding: 0.15rem 0.45rem;
  border-radius: 999px;
  margin-left: 0.35rem;
  font-size: 0.70rem;
  letter-spacing: 0.03em;
  text-transform: none;
  background: rgba(148,163,184,0.18);
  color: inherit;
  vertical-align: middle;
  word-break: break-all;
}

@media (prefers-color-scheme: dark) {
  .model-chip {
    background: rgba(148,163,184,0.16);
  }
}


div[data-testid="stVerticalBlockBorderWrapper"]:has(.main-card-marker) {
  background: rgba(255, 255, 255, 0.62) !important;
  backdrop-filter: blur(12px) !important;
  -webkit-backdrop-filter: blur(12px) !important;
  border: 1px solid rgba(148, 163, 184, 0.16) !important;
  border-radius: 1.5rem !important;
  padding: 1.25rem 1.5rem 1.5rem 1.5rem !important;
  box-shadow: 0 20px 50px rgba(15, 23, 42, 0.08) !important;
  margin-bottom: 1.25rem;
}
@media (prefers-color-scheme: dark) {
  div[data-testid="stVerticalBlockBorderWrapper"]:has(.main-card-marker) {
    background: rgba(15, 23, 42, 0.62) !important;
    border: 1px solid rgba(148, 163, 184, 0.14) !important;
    box-shadow: 0 20px 50px rgba(2, 6, 23, 0.38) !important;
  }
}
</style>
""", unsafe_allow_html=True)

def side_class(side: str) -> str:
    if side == "FOR": return "left"
    if side == "AGAINST": return "right"
    return "judge"

def avatar_class(side: str) -> str:
    if side == "FOR": return "left"
    if side == "AGAINST": return "right"
    return "judge"

def bubble_html(speaker, side, model_name, text="", typing=False, verdict=False):
    sclass = side_class(side)
    aclass = avatar_class(side)
    align = "right" if side == "AGAINST" else "left"
    initial = speaker[0].upper()
    typing_cls = "typing" if typing else ""
    verdict_cls = "verdict" if verdict else ""
    avatar = f'<div class="avatar {aclass}">{initial}</div>'
    model_chip = f'<span class="model-chip">{model_name}</span>' if model_name else ''
    return f'<div class="msg-row {align}">' \
           f'{avatar if align == "left" else ""}' \
           f'<div class="bubble-wrap">' \
           f'<div class="bubble {sclass} {typing_cls} {verdict_cls}">' \
           f'<div class="label">{speaker} · {side} {model_chip}</div>' \
           f'<div>{text}</div>' \
           f'</div>' \
           f'</div>' \
           f'{avatar if align == "right" else ""}' \
           f'</div>'

def stream_worker(token_iter, token_queue, done_event):
    try:
        for token in token_iter:
            token_queue.put(token)
    finally:
        done_event.set()

def concurrent_stream_into_bubble(placeholder, speaker, side, model_name, token_iter, hints, hint_interval=1.1, poll_interval=0.04):
    token_queue = queue.Queue()
    done_event = threading.Event()
    worker = threading.Thread(target=stream_worker, args=(token_iter, token_queue, done_event), daemon=True)
    worker.start()
    hint_index = 0
    last_hint_switch = time.time()
    full_text = ""
    first_token_seen = False
    while True:
        got_token = False
        while True:
            try:
                token = token_queue.get_nowait()
                full_text += token
                got_token = True
                first_token_seen = True
            except queue.Empty:
                break
        if got_token or first_token_seen:
            placeholder.markdown(bubble_html(speaker, side, model_name, full_text), unsafe_allow_html=True)
        else:
            current_time = time.time()
            if current_time - last_hint_switch >= hint_interval:
                hint_index = (hint_index + 1) % len(hints)
                last_hint_switch = current_time
            placeholder.markdown(
                bubble_html(speaker, side, model_name, f"<span class='dots'>{hints[hint_index]}</span>", typing=True),
                unsafe_allow_html=True,
            )
        if done_event.is_set() and token_queue.empty():
            break
        time.sleep(poll_interval)
    return full_text.strip()

st.title("🎭 LLM Debate Arena")
st.caption("Multi-agent debate between two LLM debaters and a judge, powered by OpenRouter")

st.markdown('<div class="hero-shell">', unsafe_allow_html=True)
meta_col1, meta_col2, meta_col3, meta_col4  = st.columns([1.2, 1.2, 1.2, 1.4])
with meta_col1:
    st.markdown('<span class="meta-chip">⚡ Concurrent streaming</span>', unsafe_allow_html=True)
with meta_col2:
    st.markdown('<span class="meta-chip">🎯 Friendly demo in sample mode</span>', unsafe_allow_html=True)
with meta_col3:
    st.markdown('<span class="meta-chip">✨ Auto-generate topics</span>', unsafe_allow_html=True)
with meta_col4:
    st.markdown('<span class="meta-chip">💬 Messaging-style typing hints</span>', unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

# Setup/fetch models silently
if "free_models" not in st.session_state:
    models, fetch_error = fetch_free_text_models()
    st.session_state.free_models = models
    st.session_state.models_fetch_error = fetch_error

free_models = st.session_state.free_models
model_ids = [model.id for model in free_models]
model_labels = model_name_map(free_models)
env_defaults = default_model_ids()

# Unified main-content card containing settings, selectors, topic, and actions
with st.container(border=True):
    st.markdown('<div class="main-card-marker"></div>', unsafe_allow_html=True)
    
    # Row 1: Sliders & Domain
    col1, col2, col3 = st.columns(3)
    with col1:
        rounds = st.slider("Rounds", 1, 5, 2, step=1)
        topic_domain = st.selectbox("📌 Domain", list(PERSONA_GROUPS.keys()))
    with col2:
        word_limit = st.slider("Debater words", 50, 200, 50, step=25)
    with col3:
        judge_limit = st.slider("Judge words", 50, 250, 100, step=25)
        
    hint_interval = DEFAULT_HINT_INTERVAL
    available_personas = get_personas_for_group(topic_domain)

    # Row 2: FOR, AGAINST, JUDGE selectors
    c1, c2, c3 = st.columns(3, gap="large")
    with c1:
        st.markdown('<div style="color: #0f766e; font-weight: 800; font-size: 1.05rem; letter-spacing: 0.05em; margin-bottom: 0.5rem;">🟢 FOR</div>', unsafe_allow_html=True)
        p1 = st.selectbox("Persona", available_personas, key="persona_for")
        model_for = st.selectbox(
            "Agent",
            model_ids,
            index=resolve_default_index(free_models, env_defaults["for"]),
            format_func=lambda model_id: model_labels[model_id],
            key="agent_for",
        )
    with c2:
        st.markdown('<div style="color: #1d4ed8; font-weight: 800; font-size: 1.05rem; letter-spacing: 0.05em; margin-bottom: 0.5rem;">🔵 AGAINST</div>', unsafe_allow_html=True)
        p2 = st.selectbox(
            "Persona",
            [p for p in available_personas if p != p1],
            key="persona_against",
        )
        model_against = st.selectbox(
            "Agent",
            model_ids,
            index=resolve_default_index(free_models, env_defaults["against"]),
            format_func=lambda model_id: model_labels[model_id],
            key="agent_against",
        )
    with c3:
        st.markdown('<div style="color: #a16207; font-weight: 800; font-size: 1.05rem; letter-spacing: 0.05em; margin-bottom: 0.5rem;">👑 JUDGE</div>', unsafe_allow_html=True)
        pj = st.selectbox(
            "Persona",
            [p for p in available_personas if (p != p1) & (p != p2)],
            key="persona_judge",
        )
        model_judge = st.selectbox(
            "Agent",
            model_ids,
            index=resolve_default_index(free_models, env_defaults["judge"]),
            format_func=lambda model_id: model_labels[model_id],
            key="agent_judge",
        )

    # Row 3: Debate topic setup
    if "generated_topic" not in st.session_state:
        st.session_state.generated_topic = ""
    if "topic_key" not in st.session_state:
        st.session_state.topic_key = ""

    current_key = f"{topic_domain}|{p1}|{p2}"
    if st.session_state.topic_key != current_key:
        st.session_state.topic_key = current_key
        st.session_state.generated_topic = ""
        st.session_state.debate_complete = False
        st.session_state.rematch_mode = False
        st.session_state.verdict = ""

    if "debate_complete" not in st.session_state:
        st.session_state.debate_complete = False
    if "rematch_mode" not in st.session_state:
        st.session_state.rematch_mode = False
    if "verdict" not in st.session_state:
        st.session_state.verdict = ""

    cfg_preview = DebateConfig(rounds=rounds, word_limit=word_limit, judge_limit=judge_limit, topic_domain=topic_domain)
    engine_preview = DebateEngine.from_env(
        cfg_preview,
        model_for=model_for,
        model_against=model_against,
        model_judge=model_judge,
    )

    if not st.session_state.generated_topic:
        st.session_state.generated_topic = random.choice(TOPIC_BANK.get(topic_domain, ["Enter a debate topic."]))

    if st.session_state.rematch_mode:
        st.info(f"Rematch mode: {p1} vs {p2}. Enter a new topic to continue.")

    topic = st.text_area(
        "Debate topic",
        value=st.session_state.generated_topic,
        height=96,
        help="AI can generate a fresh topic under 50 words. You can still edit it.",
    )

    # Row 4: Action elements
    b1, b2, b3 = st.columns(3)
    with b1:
        sample_mode = st.toggle("Sample mode (No API key needed)", value=True)
    with b2:
        generate_topic_btn = st.button("✨ Generate random topic", use_container_width=True)
    with b3:
        run = st.button("▶ Start debate", type="primary", use_container_width=True)

# Display warnings below the main-card container and outside it
if st.session_state.models_fetch_error:
    st.warning(
        "Could not load the OpenRouter free model list. "
        "Using .env defaults until you refresh the page."
    )

if generate_topic_btn:
    with st.status("✨ Generating a random topic for your choice of debaters...", expanded=True) as status:
        st.write(f"Domain: {topic_domain}")
        st.write(f"Debaters: {p1} vs {p2}")
        try:
            st.session_state.generated_topic = engine_preview.generate_topic(topic_domain, p1, p2)
            status.update(label="✅ Topic ready! Feel free to edit it or start the debate directly.", state="complete", expanded=False)
        except Exception:
            status.update(label="⚠️ Automatic topic generation failed. Manually add a topic please.", state="error", expanded=False)
    st.rerun()



verdict_text = ""
judge_model = ""
transcript = []

if run:
    if not topic.strip():
        st.error("Please enter a debate topic.")
        st.stop()
    if p1 == p2:
        st.error("Choose two different debaters.")
        st.stop()

    st.markdown(f'<div class="topic-banner">📌 Domain: {topic_domain} | Topic: {topic}</div>', unsafe_allow_html=True)

    transcript = []
    judge_model = ""
    verdict_text = ""    

    if sample_mode:
        def fake_stream(text, delay=0.012):
            for ch in text:
                yield ch
                time.sleep(delay)
        samples_for = [
            "When consistency and impartiality matter, rational systems can reduce fatigue, variance, and bias in decision workflows at scale.",
            "Human institutions already fail many people through delay and inconsistency. Carefully governed AI can improve reach, speed, and baseline fairness.",
        ]
        samples_against = [
            "Every consequential decision carries moral weight. Assistance is useful, but replacement erodes accountability, empathy, and legitimacy.",
            "Historical data reflects historical injustice. Automating from that data risks amplifying old harms under a veneer of objectivity.",
        ]
        for i in range(rounds):
            p1_box = st.empty()
            t1 = concurrent_stream_into_bubble(p1_box, p1, "FOR", model_for, fake_stream(samples_for[i % len(samples_for)]), [f"{p1} is reasoning", f"{p1} is revising"], hint_interval=hint_interval)
            transcript.append({"speaker": p1, "side": "FOR", "text": t1, "domain": topic_domain})
            p2_box = st.empty()
            t2 = concurrent_stream_into_bubble(p2_box, p2, "AGAINST", model_against, fake_stream(samples_against[i % len(samples_against)]), [f"{p2} is reasoning", f"{p2} is preparing a counter-argument"], hint_interval=hint_interval)
            transcript.append({"speaker": p2, "side": "AGAINST", "text": t2, "domain": topic_domain})
        judge_box = st.empty()
        judge_model = model_judge
        verdict_text = concurrent_stream_into_bubble(judge_box, pj, "JUDGE", model_judge, fake_stream(f"After a closely contested debate, {p2} argued more persuasively. The case against full replacement centered on accountability and the risk of scaling historical bias, which proved more compelling."), [f"{pj} is reviewing both sides", f"{pj} is drafting the verdict"], hint_interval=hint_interval)
        judge_box.empty()
    else:
        cfg = DebateConfig(rounds=rounds, word_limit=word_limit, judge_limit=judge_limit, topic_domain=topic_domain)
        engine = DebateEngine.from_env(
            cfg,
            model_for=model_for,
            model_against=model_against,
            model_judge=model_judge,
        )
        if not engine.api_key:
            st.error("OPENROUTER_API_KEY not set. Enable Sample mode or add your API key.")
            st.markdown('</div>', unsafe_allow_html=True)
            st.stop()
        for i in range(rounds):
            p1_box = st.empty()
            t1 = concurrent_stream_into_bubble(p1_box, p1, "FOR", model_for, engine.generate_for_argument(topic, p1), [f"{p1} is reasoning", f"{p1} is revising"], hint_interval=hint_interval)
            transcript.append({"speaker": p1, "side": "FOR", "text": t1, "domain": topic_domain})
            p2_box = st.empty()
            t2 = concurrent_stream_into_bubble(p2_box, p2, "AGAINST", model_against, engine.generate_against_argument(topic, p2, t1), [f"{p2} is reasoning", f"{p2} is preparing a counter-argument"], hint_interval=hint_interval)
            transcript.append({"speaker": p2, "side": "AGAINST", "text": t2, "domain": topic_domain})
        judge_box = st.empty()
        judge_model = model_judge
        verdict_text = concurrent_stream_into_bubble(judge_box, pj, "JUDGE", model_judge, engine.generate_verdict(topic, pj, transcript), [f"{pj} is reviewing both sides", f"{pj} is drafting the verdict"], hint_interval=hint_interval)
        judge_box.empty()

    st.markdown(
    bubble_html(pj, "JUDGE", judge_model, verdict_text, verdict=False),
    unsafe_allow_html=True,
    )

    p1_short = p1.split(" - ")[0]
    p2_short = p2.split(" - ")[0]
    verdict_lower = verdict_text.lower()
    p1_favoured = p1_short.lower() in verdict_lower[:250] or "for" in verdict_lower[:120]
    loser = p2_short if p1_favoured else p1_short

    st.markdown(
        f"""
        <div class="rematch-banner">
          🔥 The crowd isn't satisfied. <strong>{loser}</strong> demands a rematch on a new topic.
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown('<div class="rematch-spacer"></div>', unsafe_allow_html=True)

    c1, c2 = st.columns(2, gap="medium")
    with c1:
        if st.button("⚔️ Accept the Rematch", use_container_width=True):
            st.session_state.rematch_mode = True
            st.session_state.generated_topic = ""
            st.session_state.topic_key = f"{topic_domain}|{p1}|{p2}|rematch"
            st.rerun()

    with c2:
        if st.button("🏟️ Change the Arena", use_container_width=True):
            for k in ["debate_complete", "rematch_mode", "generated_topic", "topic_key", "verdict"]:
                st.session_state.pop(k, None)
            st.rerun()    

    st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)

    export = {
        "topic": topic,
        "domain": topic_domain,
        "debater_for": p1,
        "debater_against": p2,
        "judge": pj,
        "model_for": model_for,
        "model_against": model_against,
        "model_judge": model_judge,
        "transcript": transcript,
        "verdict": verdict_text,
    }
    st.download_button("⬇️ Download transcript (JSON)", data=json.dumps(export, indent=2), file_name="debate.json", mime="application/json")
