import json
import time
import uuid
import queue
import threading
import streamlit as st
from debate_arena.engine import DebateEngine, DebateConfig
from debate_arena.personas import PERSONALITIES

st.set_page_config(page_title="LLM Debate Arena", page_icon="🎭", layout="wide")

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

  .hero-shell {
    border: 1px solid rgba(148,163,184,0.18);
    background: rgba(255,255,255,0.58);
    backdrop-filter: blur(14px); -webkit-backdrop-filter: blur(14px);
    border-radius: 1.4rem; padding: 1.1rem 1.1rem 0.9rem 1.1rem;
    box-shadow: 0 14px 40px rgba(15,23,42,0.08); margin-bottom: 1rem;
  }
  @media (prefers-color-scheme: dark) {
    .hero-shell {
      background: rgba(15,23,42,0.64);
      border: 1px solid rgba(148,163,184,0.15);
      box-shadow: 0 14px 40px rgba(2,6,23,0.42);
    }
  }

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
    transition: all 180ms ease;
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
  @media (prefers-color-scheme: dark) {
    .bubble.left.typing  { background: linear-gradient(180deg, #0d231d 0%, #0b1d18 100%); color: #a7f3d0; }
    .bubble.right.typing { background: linear-gradient(180deg, #101b31 0%, #0c1728 100%); color: #bfdbfe; }
    .bubble.judge.typing { background: linear-gradient(180deg, #2f220d 0%, #241b0c 100%); color: #fde68a; }
  }

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
  @keyframes dots {
    0% { content: ""; } 25% { content: "."; } 50% { content: ".."; } 75% { content: "..."; } 100% { content: ""; }
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
</style>
""", unsafe_allow_html=True)


def side_class(side: str) -> str:
    if side == "FOR":
        return "left"
    if side == "AGAINST":
        return "right"
    return "judge"


def avatar_class(side: str) -> str:
    if side == "FOR":
        return "left"
    if side == "AGAINST":
        return "right"
    return "judge"


def bubble_html(speaker, side, text="", typing=False):
    sclass = side_class(side)
    aclass = avatar_class(side)
    align = "right" if side == "AGAINST" else "left"
    initial = speaker[0].upper()
    typing_cls = "typing" if typing else ""
    avatar = f'<div class="avatar {aclass}">{initial}</div>'
    return f"""
    <div class="msg-row {align}">
      {avatar if align == 'left' else ''}
      <div class="bubble-wrap">
        <div class="bubble {sclass} {typing_cls}">
          <div class="label">{speaker} · {side}</div>
          <div>{text}</div>
        </div>
      </div>
      {avatar if align == 'right' else ''}
    </div>
    """


def smooth_scroll_to_bottom():
    anchor = f"scroll-anchor-{uuid.uuid4().hex}"
    st.markdown(
        f"""
        <div id="{anchor}"></div>
        <script>
        const el = window.parent.document.getElementById('{anchor}') || document.getElementById('{anchor}');
        if (el) el.scrollIntoView({{ behavior: 'smooth', block: 'end' }});
        </script>
        """,
        unsafe_allow_html=True,
    )


def stream_worker(token_iter, token_queue, done_event):
    try:
        for token in token_iter:
            token_queue.put(token)
    finally:
        done_event.set()


def concurrent_stream_into_bubble(placeholder, speaker, side, token_iter, hints, hint_interval=1.1, poll_interval=0.04):
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
            placeholder.markdown(bubble_html(speaker, side, full_text), unsafe_allow_html=True)
        else:
            current_time = time.time()
            if current_time - last_hint_switch >= hint_interval:
                hint_index = (hint_index + 1) % len(hints)
                last_hint_switch = current_time
            placeholder.markdown(
                bubble_html(speaker, side, f"<span class='dots'>{hints[hint_index]}</span>", typing=True),
                unsafe_allow_html=True,
            )

        if done_event.is_set() and token_queue.empty():
            break
        time.sleep(poll_interval)

    return full_text.strip()


st.title("🎭 LLM Debate Arena")
st.caption("Multi-agent debate between two LLM debaters and a judge, powered by OpenRouter")

hero_container = st.container()
with hero_container:
    meta_col1, meta_col2, meta_col3 = st.columns([1.2, 1.2, 2.6])
    with meta_col1:
        st.markdown('<span class="meta-chip">⚡ Concurrent streaming</span>', unsafe_allow_html=True)
    with meta_col2:
        st.markdown('<span class="meta-chip">🎯 Friendly demo</span>', unsafe_allow_html=True)
    with meta_col3:
        st.markdown('<span class="meta-chip">💬 Real wait-time typing hints</span>', unsafe_allow_html=True)

with st.sidebar:
    st.header("⚙️ Settings")
    rounds = st.slider("Rounds", 1, 5, 2, step=1)
    word_limit = st.slider("Debater word limit", 50, 200, 50, step=25)
    judge_limit = st.slider("Judge word limit", 50, 250, 100, step=25)
    #hint_interval = st.slider("Hint change speed (sec)", 0.5, 5.0, 4.0, step=0.5)
    hint_interval = 4.0
    p1 = st.selectbox("Debater 1 (FOR)", PERSONALITIES, index=0)
    p2 = st.selectbox("Debater 2 (AGAINST)", PERSONALITIES, index=1)
    pj = st.selectbox("Judge", PERSONALITIES, index=2)
    sample_mode = st.toggle("Sample mode (no API key needed)", value=True)
    run = st.button("▶ Start debate", type="primary", use_container_width=True)
    st.markdown("---")
    st.markdown("Typing hints now run **while the model request is already in progress**.")

topic = st.text_area(
    "Debate topic",
    value="Should AI replace human decision-making in critical domains like healthcare and justice?",
    height=96,
    help="Both debaters will argue from opposing sides.",
)

if run:
    if not topic.strip():
        st.error("Please enter a debate topic.")
        st.stop()

    st.markdown(f'<div class="topic-banner">📌 Topic: {topic}</div>', unsafe_allow_html=True)

    transcript = []
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
            t1 = concurrent_stream_into_bubble(
                p1_box, p1, "FOR",
                fake_stream(samples_for[i % len(samples_for)]),
                [f"{p1} is reasoning", f"{p1} is preparing an argument"],
                hint_interval=hint_interval,
            )
            transcript.append({"speaker": p1, "side": "FOR", "text": t1})
            smooth_scroll_to_bottom()

            p2_box = st.empty()
            t2 = concurrent_stream_into_bubble(
                p2_box, p2, "AGAINST",
                fake_stream(samples_against[i % len(samples_against)]),
                [f"{p2} is reasoning", f"{p2} is preparing a counter-argument"],
                hint_interval=hint_interval,
            )
            transcript.append({"speaker": p2, "side": "AGAINST", "text": t2})
            smooth_scroll_to_bottom()

        judge_box = st.empty()
        verdict_text = concurrent_stream_into_bubble(
            judge_box, pj, "JUDGE",
            fake_stream(
                f"After a closely contested debate, {p2} argued more persuasively. The case against full replacement centered on accountability and the risk of scaling historical bias, which proved more compelling.",
                delay=0.012,
            ),
            [f"{pj} is reviewing both sides", f"{pj} is drafting the verdict"],
            hint_interval=hint_interval,
        )
        judge_box.empty()
        smooth_scroll_to_bottom()

    else:
        cfg = DebateConfig(rounds=rounds, word_limit=word_limit, judge_limit=judge_limit)
        engine = DebateEngine.from_env(cfg)
        if not engine.api_key:
            st.error("OPENROUTER_API_KEY not set. Enable Sample mode or add your API key.")
            st.markdown('</div>', unsafe_allow_html=True)
            st.stop()

        for i in range(rounds):
            p1_box = st.empty()
            t1 = concurrent_stream_into_bubble(
                p1_box, p1, "FOR",
                engine.generate_for_argument(topic, p1),
                [f"{p1} is reasoning", f"{p1} is preparing an argument"],
                hint_interval=hint_interval,
            )
            transcript.append({"speaker": p1, "side": "FOR", "text": t1})
            smooth_scroll_to_bottom()

            p2_box = st.empty()
            t2 = concurrent_stream_into_bubble(
                p2_box, p2, "AGAINST",
                engine.generate_against_argument(topic, p2, t1),
                [f"{p2} is reasoning", f"{p2} is preparing a counter-argument"],
                hint_interval=hint_interval,
            )
            transcript.append({"speaker": p2, "side": "AGAINST", "text": t2})
            smooth_scroll_to_bottom()

        judge_box = st.empty()
        verdict_text = concurrent_stream_into_bubble(
            judge_box, pj, "JUDGE",
            engine.generate_verdict(topic, pj, transcript),
            [f"{pj} is reviewing both sides", f"{pj} is drafting the verdict"],
            hint_interval=hint_interval,
        )
        judge_box.empty()
        smooth_scroll_to_bottom()

    st.markdown(f"""
    <div class="verdict-box">
      <div class="verdict-title">⚖️ Judge's Verdict — {pj}</div>
      <div>{verdict_text}</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)

    export = {
        "topic": topic,
        "debater_for": p1,
        "debater_against": p2,
        "judge": pj,
        "transcript": transcript,
        "verdict": verdict_text,
    }
    st.download_button(
        "⬇ Download transcript (JSON)",
        data=json.dumps(export, indent=2),
        file_name="debate.json",
        mime="application/json",
    )
