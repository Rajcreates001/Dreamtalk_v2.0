"""
DreamTalk Emotion Visualization Dashboard
===========================================
Real-time dashboard showing:
  - PAD (Pleasure-Arousal-Dominance) coordinates
  - Mood state with confidence distribution
  - Brain area activations
  - Sentiment analysis
  - Emotion history tracking
"""

import os
import sys
import time
import json
from datetime import datetime
from collections import deque

# Must be first to avoid torch DLL conflicts
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

# Add project root to path
_proj = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _proj not in sys.path:
    sys.path.insert(0, _proj)

from dreamtalk.pipeline.brain_pipeline import (
    TextEmotionDetector, BrainPipeline, MoodState, PAD_MOOD_MAP,
    PFCBrainArea, dACCBrainArea, InsulaBrainArea, IPLBrainArea, BasalGangliaBrainArea,
)
from dreamtalk.emotion.core.pad_model import PADEmotionEngine

# ─── Page Config ──────────────────────────────────────────────────────────
st.set_page_config(
    page_title="DreamTalk Emotion Dashboard",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Session State Init ──────────────────────────────────────────────────
if "emotion_history" not in st.session_state:
    st.session_state.emotion_history = deque(maxlen=50)
if "pad_history" not in st.session_state:
    st.session_state.pad_history = deque(maxlen=50)
if "mood_history" not in st.session_state:
    st.session_state.mood_history = deque(maxlen=50)
if "brain_history" not in st.session_state:
    st.session_state.brain_history = deque(maxlen=50)
if "timestamps" not in st.session_state:
    st.session_state.timestamps = deque(maxlen=50)
if "detector" not in st.session_state:
    st.session_state.detector = TextEmotionDetector()
if "pad_engine" not in st.session_state:
    st.session_state.pad_engine = PADEmotionEngine(inertia=0.85)
if "counter" not in st.session_state:
    st.session_state.counter = 0

# ─── Color Palette ───────────────────────────────────────────────────────
MOOD_COLORS = {
    "happy": "#FFD700", "excited": "#FF6B00", "calm": "#4ECDC4",
    "content": "#7B68EE", "sad": "#4A90D9", "angry": "#FF4444",
    "furious": "#CC0000", "fearful": "#9B59B6", "anxious": "#E67E22",
    "surprised": "#F1C40F", "disgusted": "#2ECC71", "frustrated": "#E74C3C",
    "loving": "#FF69B4", "hopeful": "#00BFFF", "grateful": "#2ECC71",
    "confused": "#95A5A6", "trusting": "#1ABC9C", "neutral": "#BDC3C7",
    "pity": "#8E44AD", "betrayal": "#C0392B", "haste": "#E67E22",
    "defensive": "#D35400", "annoyed": "#E67E22", "playful": "#FF69B4",
    "sarcastic": "#9B59B6", "hurt": "#34495E",
}

BRAIN_AREA_COLORS = {
    "PFC": "#3498DB", "dACC": "#E74C3C", "Insula": "#2ECC71",
    "IPL": "#F39C12", "BasalGanglia": "#9B59B6",
}

QUICK_EMOTION_SAMPLES = [
    "I am so incredibly happy and joyful today!",
    "I'm feeling so sad and depressed... lonely and heartbroken.",
    "I hate this! You are so stupid and terrible! I'm furious!",
    "Oh you poor thing, I feel so sorry for you. How tragic.",
    "I trusted you and you betrayed me! You lied and deceived me!",
    "Hurry up! We need this urgently, right now! No time to waste!",
    "I trust you completely. You are honest, reliable, and faithful.",
    "I hope things get better. I'm optimistic about the future.",
    "I love you so much! You're such a wonderful person!",
    "I'm terrified and scared. I feel so anxious and worried.",
    "Hello, how are you today? The weather is nice.",
]

# ─── Title ───────────────────────────────────────────────────────────────
st.title("🧠 DreamTalk Emotion Dashboard")
st.markdown("Real-time PAD emotion tracking, brain area activations, and sentiment analysis")


# ═══════════════════════════════════════════════════════════════════════════
# SIDEBAR — Controls
# ═══════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.header("Controls")

    input_mode = st.radio("Input mode", ["Text input", "Quick test emotions"], index=0)

    if input_mode == "Text input":
        user_text = st.text_area(
            "Enter text to analyze",
            "I am so happy and excited today! This is wonderful!",
            height=100,
            key="text_input",
        )
        analyze_btn = st.button("Analyze", type="primary", use_container_width=True)
    else:
        if "_next_text" in st.session_state and st.session_state["_next_text"] in QUICK_EMOTION_SAMPLES:
            default_idx = QUICK_EMOTION_SAMPLES.index(st.session_state.pop("_next_text"))
            selected = st.selectbox("Select emotion to test", QUICK_EMOTION_SAMPLES, index=default_idx, key="qb_sel")
        else:
            selected = st.selectbox("Select emotion to test", QUICK_EMOTION_SAMPLES, index=0, key="qb_sel")
        user_text = selected
        analyze_btn = st.button("Analyze", type="primary", use_container_width=True)

    st.divider()
    st.caption("Auto-rotate every 3s" if input_mode == "Quick test emotions" else "Manual analysis")

    clear_btn = st.button("Clear history", use_container_width=True)
    if clear_btn:
        st.session_state.emotion_history.clear()
        st.session_state.pad_history.clear()
        st.session_state.mood_history.clear()
        st.session_state.brain_history.clear()
        st.session_state.timestamps.clear()
        st.rerun()


# ═══════════════════════════════════════════════════════════════════════════
# ANALYSIS FUNCTION
# ═══════════════════════════════════════════════════════════════════════════
def run_analysis(text: str):
    ts = datetime.now().strftime("%H:%M:%S")
    detector = st.session_state.detector
    pad_engine = st.session_state.pad_engine

    try:
        # 1. Text emotion detection
        emotion = detector.analyze(text)
    except Exception as e:
        st.error(f"Emotion detection failed: {e}")
        return None, None, None

    try:
        # 2. PAD engine update
        pad_state = pad_engine.update((emotion.valence, emotion.arousal, emotion.dominance))
    except Exception as e:
        st.error(f"PAD update failed: {e}")
        pad_state = {"pad": (0, 0, 0), "name": "neutral"}

    # 3. Brain area simulation — modulated by emotion intensity
    pfc = PFCBrainArea()
    dacc = dACCBrainArea()
    insula = InsulaBrainArea()
    ipl = IPLBrainArea()
    bg = BasalGangliaBrainArea()

    import numpy as np
    intensity_mod = max(emotion.intensity_score * 3, 0.1)
    valence_bias = emotion.valence * 0.3
    arousal_bias = emotion.arousal * 0.3

    inp = np.random.randn(256) * 0.1 + valence_bias * 0.1
    pfc_out = pfc.forward(inp)
    dacc_out = dacc.forward(pfc_out)
    # Modulate dACC conflict by emotional intensity
    dacc.conflict_score = max(0, min(1, dacc.conflict_score * (0.5 + intensity_mod * 0.5)))

    insula_inp = np.random.randn(64) * 0.1 + arousal_bias * 0.15
    insula_out = insula.forward(insula_inp, text)
    insula.emotional_valence = emotion.valence

    ipl_out = ipl.forward()
    bg_action = bg.forward(pfc_out, dacc.conflict_score, insula_out)

    brain_states = {
        "PFC": {"firing": pfc.firing_rate, "potential": float(np.mean(pfc.membrane_potential)),
                "spikes": pfc.spike_count, "dopamine": pfc.dopamine, "learning": pfc.dopamine * 0.01},
        "dACC": {"firing": dacc.firing_rate, "potential": float(np.mean(dacc.membrane_potential)),
                 "spikes": dacc.spike_count, "conflict": dacc.conflict_score,
                 "learning": 0.01 * (1.0 - dacc.conflict_score)},
        "Insula": {"firing": insula.firing_rate, "potential": float(np.mean(insula.membrane_potential)),
                   "spikes": insula.spike_count, "valence": insula.emotional_valence, "learning": 0.01},
        "IPL": {"firing": ipl.firing_rate, "potential": float(np.mean(ipl.membrane_potential)),
                "spikes": ipl.spike_count, "learning": 0.005},
        "BasalGanglia": {"firing": bg.firing_rate, "potential": float(np.mean(bg.membrane_potential)),
                         "spikes": bg.spike_count, "action": bg_action, "value": bg.action_value, "learning": 0.01},
    }

    pad_entry = {"pleasure": pad_state["pad"][0], "arousal": pad_state["pad"][1], "dominance": pad_state["pad"][2]}

    # Store history
    st.session_state.timestamps.append(ts)
    st.session_state.emotion_history.append({
        "mood": emotion.primary_mood.value,
        "valence": emotion.valence,
        "arousal": emotion.arousal,
        "dominance": emotion.dominance,
        "intensity": emotion.intensity,
        "intensity_score": emotion.intensity_score,
        "confidence": emotion.confidence,
        "is_hostile": emotion.is_hostile,
        "compound": emotion.sentiment_compound,
        "pos": emotion.sentiment_pos,
        "neg": emotion.sentiment_neg,
        "neu": emotion.sentiment_neu,
    })
    st.session_state.pad_history.append(pad_entry)
    st.session_state.mood_history.append({
        "mood": emotion.primary_mood.value,
        "confidences": emotion.mood_confidences,
    })
    st.session_state.brain_history.append(brain_states)

    return emotion, pad_state, brain_states


# ═══════════════════════════════════════════════════════════════════════════
# MAIN DASHBOARD LAYOUT
# ═══════════════════════════════════════════════════════════════════════════

# Trigger analysis on button click
if analyze_btn:
    emotion, pad_state, brain_states = run_analysis(user_text)
    if emotion is not None:
        st.session_state.counter += 1
        st.rerun()

# Also run on first load
if st.session_state.counter == 0:
    emotion, pad_state, brain_states = run_analysis(user_text)
    if emotion is not None:
        st.session_state.counter += 1
        st.rerun()

# Auto-refresh trigger from Quick Test timer (non-blocking)
if st.session_state.pop("_trigger_analysis", False):
    emotion, pad_state, brain_states = run_analysis(user_text)
    if emotion is not None:
        st.session_state.counter += 1

# Get latest data
if st.session_state.emotion_history:
    latest = st.session_state.emotion_history[-1]
    latest_pad = st.session_state.pad_history[-1] if st.session_state.pad_history else {"pleasure": 0, "arousal": 0, "dominance": 0}
    latest_mood = st.session_state.mood_history[-1] if st.session_state.mood_history else {"mood": "neutral", "confidences": {}}
    latest_brain = st.session_state.brain_history[-1] if st.session_state.brain_history else {}
else:
    latest = {"mood": "neutral", "valence": 0, "arousal": 0, "dominance": 0, "intensity": "low",
              "intensity_score": 0, "confidence": 0, "is_hostile": False, "compound": 0,
              "pos": 0, "neg": 0, "neu": 0}
    latest_pad = {"pleasure": 0, "arousal": 0, "dominance": 0}
    latest_mood = {"mood": "neutral", "confidences": {}}
    latest_brain = {}

# ─── Row 1: PAD 3D + Mood + Intensity ───────────────────────────────────
row1 = st.columns([2, 1, 1])

with row1[0]:
    st.subheader("🎯 PAD Emotion Space")

    # 3D PAD scatter plot
    pad_df = pd.DataFrame(st.session_state.pad_history) if st.session_state.pad_history else pd.DataFrame(
        {"pleasure": [0], "arousal": [0], "dominance": [0]})
    pad_df["time"] = list(st.session_state.timestamps) if st.session_state.timestamps else ["now"]
    pad_df["mood"] = [e["mood"] for e in st.session_state.emotion_history] if st.session_state.emotion_history else ["neutral"]

    fig_pad = go.Figure()

    # Add trajectory line
    if len(pad_df) > 1:
        fig_pad.add_trace(go.Scatter3d(
            x=pad_df["pleasure"], y=pad_df["arousal"], z=pad_df["dominance"],
            mode="lines+markers",
            marker=dict(size=6, color=list(range(len(pad_df))), colorscale="Viridis", showscale=True,
                        colorbar=dict(title="Time", x=1.02)),
            line=dict(color="rgba(100,100,255,0.4)", width=2),
            text=pad_df["mood"] + "<br>" + pad_df["time"],
            hoverinfo="text",
            name="Trajectory",
        ))

    # Mark current position
    if len(pad_df) > 0:
        last = pad_df.iloc[-1]
        color = MOOD_COLORS.get(latest["mood"], "#BDC3C7")
        fig_pad.add_trace(go.Scatter3d(
            x=[last["pleasure"]], y=[last["arousal"]], z=[last["dominance"]],
            mode="markers",
            marker=dict(size=16, color=color, symbol="diamond",
                        line=dict(color="white", width=2)),
            name=f'Current: {latest["mood"]}',
            text=f'{latest["mood"]}<br>P={last["pleasure"]:.2f} A={last["arousal"]:.2f} D={last["dominance"]:.2f}',
            hoverinfo="text",
        ))

    # Add reference planes
    fig_pad.add_trace(go.Scatter3d(x=[-1, 1], y=[0, 0], z=[0, 0], mode="lines",
                                   line=dict(color="rgba(200,200,200,0.2)", width=1), showlegend=False,
                                   hoverinfo="skip"))
    fig_pad.add_trace(go.Scatter3d(x=[0, 0], y=[-1, 1], z=[0, 0], mode="lines",
                                   line=dict(color="rgba(200,200,200,0.2)", width=1), showlegend=False,
                                   hoverinfo="skip"))
    fig_pad.add_trace(go.Scatter3d(x=[0, 0], y=[0, 0], z=[-1, 1], mode="lines",
                                   line=dict(color="rgba(200,200,200,0.2)", width=1), showlegend=False,
                                   hoverinfo="skip"))

    fig_pad.update_layout(
        height=400,
        margin=dict(l=0, r=0, t=0, b=0),
        scene=dict(
            xaxis=dict(title="Pleasure", range=[-1, 1], zerolinecolor="rgba(200,200,200,0.3)"),
            yaxis=dict(title="Arousal", range=[-1, 1], zerolinecolor="rgba(200,200,200,0.3)"),
            zaxis=dict(title="Dominance", range=[-1, 1], zerolinecolor="rgba(200,200,200,0.3)"),
            bgcolor="rgba(0,0,0,0)",
            camera=dict(eye=dict(x=1.5, y=1.5, z=1.5)),
        ),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        hovermode="closest",
    )
    st.plotly_chart(fig_pad, use_container_width=True)

with row1[1]:
    st.subheader("😊 Current Mood")
    mood_name = latest["mood"]
    mood_color = MOOD_COLORS.get(mood_name, "#BDC3C7")

    # Large mood emoji
    mood_emojis = {
        "happy": "😄", "excited": "🤩", "calm": "😌", "content": "😊",
        "sad": "😢", "angry": "😠", "furious": "🤬", "fearful": "😨",
        "anxious": "😰", "surprised": "😲", "disgusted": "🤢", "frustrated": "😤",
        "loving": "🥰", "hopeful": "🤞", "grateful": "🙏", "confused": "😕",
        "trusting": "🤝", "neutral": "😐", "pity": "🥺", "betrayal": "💔",
        "haste": "🏃", "defensive": "🛡️", "annoyed": "🙄", "playful": "😏",
        "sarcastic": "😏", "hurt": "😔",
    }
    emoji = mood_emojis.get(mood_name, "🤖")

    st.markdown(
        f"""
        <div style="text-align:center; padding:20px; background:{mood_color}22; border-radius:15px; border:2px solid {mood_color};">
            <div style="font-size:72px;">{emoji}</div>
            <div style="font-size:28px; font-weight:bold; margin-top:10px; color:{mood_color};">{mood_name.upper()}</div>
            <div style="font-size:16px; margin-top:5px;">Intensity: <b>{latest.get("intensity", "low")}</b> ({latest.get("intensity_score", 0):.2f})</div>
            <div style="font-size:14px; color:gray;">Confidence: {latest.get("confidence", 0):.3f}</div>
            <div style="font-size:14px; color:gray;">Hostile: {'⚠️ Yes' if latest.get('is_hostile') else '✅ No'}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Mood confidence distribution (top 5)
    confs = latest_mood.get("confidences", {})
    if confs:
        sorted_confs = sorted(confs.items(), key=lambda x: x[1], reverse=True)[:8]
        conf_df = pd.DataFrame(sorted_confs, columns=["Mood", "Confidence"])
        conf_df["Color"] = conf_df["Mood"].map(MOOD_COLORS).fill("#BDC3C7")

        fig_conf = go.Figure(go.Bar(
            x=conf_df["Confidence"],
            y=conf_df["Mood"],
            orientation="h",
            marker_color=conf_df["Color"],
            text=conf_df["Confidence"].round(3),
            textposition="outside",
            hovertemplate="%{y}: %{x:.3f}<extra></extra>",
        ))
        fig_conf.update_layout(
            height=250,
            margin=dict(l=0, r=0, t=0, b=0),
            xaxis=dict(title="Score", range=[0, max(conf_df["Confidence"]) * 1.3 if len(conf_df) > 0 else 1]),
            yaxis=dict(title=""),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            bargap=0.2,
        )
        st.plotly_chart(fig_conf, use_container_width=True)

with row1[2]:
    st.subheader("📊 PAD Gauges")

    def pad_gauge(value, title, color, min_v=-1, max_v=1):
        fig = go.Figure(go.Indicator(
            mode="gauge+number",
            value=value,
            number=dict(suffix="", font=dict(size=24, color=color)),
            gauge=dict(
                axis=dict(range=[min_v, max_v], tickwidth=1, tickcolor="gray",
                          tickvals=[-1, -0.5, 0, 0.5, 1]),
                bar=dict(color=color, thickness=0.6),
                bgcolor="rgba(0,0,0,0)",
                borderwidth=1,
                bordercolor="rgba(200,200,200,0.3)",
                threshold=dict(
                    line=dict(color="white", width=2),
                    thickness=0.75,
                    value=value,
                ),
            ),
        ))
        fig.update_layout(
            height=130,
            margin=dict(l=20, r=20, t=25, b=10),
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color="white"),
            title=dict(text=title, font=dict(size=14, color="white"), x=0.5),
        )
        return fig

    col_a, col_b, col_c = st.columns(3)
    with col_a:
        st.plotly_chart(pad_gauge(latest_pad["pleasure"], "Pleasure", "#FFD700"),
                        use_container_width=True)
    with col_b:
        st.plotly_chart(pad_gauge(latest_pad["arousal"], "Arousal", "#FF6B00"),
                        use_container_width=True)
    with col_c:
        st.plotly_chart(pad_gauge(latest_pad["dominance"], "Dominance", "#4ECDC4"),
                        use_container_width=True)

    # Sentiment breakdown
    st.subheader("📈 Sentiment")
    sent_fig = go.Figure(go.Bar(
        x=["Positive", "Negative", "Neutral"],
        y=[latest.get("pos", 0), latest.get("neg", 0), latest.get("neu", 0)],
        marker_color=["#2ECC71", "#E74C3C", "#BDC3C7"],
        text=[f"{latest.get('pos', 0):.1%}", f"{latest.get('neg', 0):.1%}", f"{latest.get('neu', 0):.1%}"],
        textposition="outside",
    ))
    sent_fig.update_layout(
        height=150,
        margin=dict(l=0, r=0, t=0, b=0),
        yaxis=dict(title="", range=[0, 1]),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        bargap=0.3,
        showlegend=False,
    )
    st.plotly_chart(sent_fig, use_container_width=True)

    valence_trend = latest.get('valence_trend', 'stable')
    st.caption(f"Compound: {latest.get('compound', 0):+.3f} | V-Trend: {valence_trend}")


# ─── Row 2: Brain Area Activations + Mood History ────────────────────────
row2 = st.columns([1.5, 1])

with row2[0]:
    st.subheader("🧠 Brain Area Activations")

    if latest_brain:
        areas = list(latest_brain.keys())
        firing_rates = [latest_brain[a]["firing"] * 100 for a in areas]
        potentials = [latest_brain[a]["potential"] for a in areas]
        colors = [BRAIN_AREA_COLORS.get(a, "#BDC3C7") for a in areas]

        # Firing rates bar chart
        fig_brain = go.Figure()
        fig_brain.add_trace(go.Bar(
            name="Firing Rate (Hz)", x=areas, y=firing_rates,
            marker_color=colors,
            text=[f"{v:.1f} Hz" for v in firing_rates],
            textposition="outside",
            offsetgroup=0,
        ))
        fig_brain.add_trace(go.Bar(
            name="Membrane Potential", x=areas,
            y=[abs(p) * 10 for p in potentials],
            marker_color=[c + "88" for c in colors],
            text=[f"{p:.3f}" for p in potentials],
            textposition="outside",
            offsetgroup=1,
        ))
        fig_brain.update_layout(
            barmode="group",
            height=250,
            margin=dict(l=0, r=0, t=0, b=0),
            yaxis=dict(title="", range=[0, max(max(firing_rates) * 1.3, 5) if firing_rates else 5]),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            legend=dict(orientation="h", y=1.1),
        )
        st.plotly_chart(fig_brain, use_container_width=True)

        # BG action and dACC conflict
        bg_info = latest_brain.get("BasalGanglia", {})
        dacc_info = latest_brain.get("dACC", {})
        info_cols = st.columns(4)
        with info_cols[0]:
            st.metric("BG Action", bg_info.get("action", "N/A"), delta=None,
                      delta_color="off")
        with info_cols[1]:
            st.metric("BG Value", f"{bg_info.get('value', 0):.3f}",
                      delta=None, delta_color="off")
        with info_cols[2]:
            st.metric("dACC Conflict", f"{dacc_info.get('conflict', 0):.3f}",
                      delta=None, delta_color="off")
        with info_cols[3]:
            insula_info = latest_brain.get("Insula", {})
            st.metric("Insula Valence", f"{insula_info.get('valence', 0):+.3f}",
                      delta=None, delta_color="off")

    else:
        st.info("Run an analysis to see brain activations")

with row2[1]:
    st.subheader("📉 Mood Timeline")

    if len(st.session_state.emotion_history) > 1:
        hist = list(st.session_state.emotion_history)
        times = list(st.session_state.timestamps)
        moods = [h["mood"] for h in hist]
        intensities = [h["intensity_score"] for h in hist]

        # Color mapping for mood trace
        mood_colors_list = [MOOD_COLORS.get(m, "#BDC3C7") for m in moods]

        fig_timeline = go.Figure()
        fig_timeline.add_trace(go.Scatter(
            x=list(range(len(hist))),
            y=[h["valence"] for h in hist],
            mode="lines+markers",
            name="Valence",
            line=dict(color="#FFD700", width=3),
            marker=dict(size=8, color=mood_colors_list, line=dict(color="white", width=1)),
            text=[f"{m}<br>{t}<br>V={h['valence']:+.2f}" for m, t, h in zip(moods, times, hist)],
            hoverinfo="text",
        ))
        fig_timeline.add_trace(go.Scatter(
            x=list(range(len(hist))),
            y=[h["arousal"] for h in hist],
            mode="lines+markers",
            name="Arousal",
            line=dict(color="#FF6B00", width=2, dash="dot"),
            marker=dict(size=6, symbol="triangle-up"),
        ))

        fig_timeline.update_layout(
            height=250,
            margin=dict(l=0, r=0, t=0, b=0),
            xaxis=dict(title="Time Step", showticklabels=False),
            yaxis=dict(title="", range=[-1, 1]),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            legend=dict(orientation="h", y=1.1),
            hovermode="x unified",
        )
        st.plotly_chart(fig_timeline, use_container_width=True)

        # Mood distribution over time (heatmap style)
        mood_counts = pd.Series(moods).value_counts()
        top_moods = mood_counts.head(8).index.tolist()
        mood_df = pd.DataFrame({
            "Mood": moods[-20:] if len(moods) > 20 else moods,
            "Step": list(range(max(0, len(moods) - 20), len(moods))) if len(moods) > 20 else list(range(len(moods))),
        })
        mood_cross = pd.crosstab(mood_df["Step"], mood_df["Mood"])
        # Reindex to include all top moods
        for m in top_moods:
            if m not in mood_cross.columns:
                mood_cross[m] = 0

        fig_dist = go.Figure()
        for m in top_moods:
            color = MOOD_COLORS.get(m, "#BDC3C7")
            if m in mood_cross.columns:
                fig_dist.add_trace(go.Bar(
                    name=m,
                    x=mood_cross.index,
                    y=mood_cross[m],
                    marker_color=color,
                    hovertemplate=f"{m}<extra></extra>",
                ))

        fig_dist.update_layout(
            barmode="stack",
            height=100,
            margin=dict(l=0, r=0, t=0, b=0),
            xaxis=dict(showticklabels=False, title=""),
            yaxis=dict(title="", showticklabels=False),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            showlegend=True,
            legend=dict(orientation="h", y=-0.2, font=dict(size=9)),
        )
        st.plotly_chart(fig_dist, use_container_width=True)

    else:
        st.info("Analyze more inputs to see timeline")


# ─── Row 3: Input text and raw data ──────────────────────────────────────
row3 = st.columns([1, 1])

with row3[0]:
    with st.expander("📝 Current Analysis Details", expanded=True):
        if st.session_state.emotion_history:
            details = st.session_state.emotion_history[-1]
            detail_cols = st.columns(3)
            with detail_cols[0]:
                st.metric("Primary Mood", details.get("mood", "N/A").title())
                st.metric("Valence", f"{details.get('valence', 0):+.3f}")
                st.metric("Arousal", f"{details.get('arousal', 0):.3f}")
            with detail_cols[1]:
                st.metric("Dominance", f"{details.get('dominance', 0):.3f}")
                st.metric("Intensity", f"{details.get('intensity_score', 0):.3f} ({details.get('intensity', 'low')})")
                st.metric("Confidence", f"{details.get('confidence', 0):.3f}")
            with detail_cols[2]:
                st.metric("Sentiment", f"{details.get('compound', 0):+.3f}")
                st.metric("Hostile", "Yes" if details.get("is_hostile") else "No")
                st.metric("P:V:A:D", f"({details.get('pos',0):.2f}/{details.get('neg',0):.2f}/{details.get('neu',0):.2f})")

with row3[1]:
    with st.expander("📋 Raw JSON", expanded=False):
        if st.session_state.emotion_history:
            raw = st.session_state.emotion_history[-1]
            st.json(raw)


# ─── Auto-refresh for Quick Test mode (non-blocking) ──────────────────────
if input_mode == "Quick test emotions":
    st.toast(f"Analyzed: {latest.get('mood', 'N/A')}", icon="🧠")
    st.markdown(
        """
        <div style="text-align:center; margin:10px 0;">
            <span style="color:#F39C12; font-size:14px;">
                🔄 Auto-rotating through emotion samples (next in 3s)
            </span>
        </div>
        """,
        unsafe_allow_html=True,
    )
    # Use session state timer to schedule next analysis
    now = time.monotonic()
    if "_next_scan" not in st.session_state:
        st.session_state["_next_scan"] = now + 3.0
        st.rerun()
    elif now >= st.session_state["_next_scan"]:
        st.session_state["_next_scan"] = now + 3.0
        # Rotate to next emotion in the list
        current_idx = QUICK_EMOTION_SAMPLES.index(user_text) if user_text in QUICK_EMOTION_SAMPLES else -1
        next_idx = (current_idx + 1) % len(QUICK_EMOTION_SAMPLES)
        st.session_state["_next_text"] = QUICK_EMOTION_SAMPLES[next_idx]
        st.session_state["_trigger_analysis"] = True
        st.rerun()


# ─── Footer ──────────────────────────────────────────────────────────────
st.divider()
col_f = st.columns(3)
with col_f[0]:
    st.caption(f"Analyses run: {st.session_state.counter}")
with col_f[1]:
    st.caption(f"History size: {len(st.session_state.emotion_history)}")
with col_f[2]:
    st.caption("DreamTalk Emotion Dashboard v1.0")
