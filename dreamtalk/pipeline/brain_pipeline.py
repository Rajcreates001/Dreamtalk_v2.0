"""Brain Pipeline v2 — SNN Brain Areas → Multi-Encoder → STDP Learning → PAD Emotion → Decision."""

import json
import logging
import math
import os
import random
import re
import time
import uuid
from collections import deque
from typing import Optional, List, Tuple, Dict, Any, Callable

import numpy as np

from dreamtalk.pipeline.models import (
    BrainDecisionResult,
    EmotionResult,
    ObjectDetectionResult,
    MoodState,
    BrainAreaActivation,
    SpikingActivity,
)

logger = logging.getLogger("dreamtalk.pipeline.brain")

TORCH_AVAILABLE = False
try:
    import torch
    _ = torch.tensor([1.0])
    TORCH_AVAILABLE = True
    import torch.nn as nn
except Exception:
    pass

try:
    import cv2
    CV2_AVAILABLE = True
except Exception:
    CV2_AVAILABLE = False

try:
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
    VADER_AVAILABLE = True
except Exception:
    VADER_AVAILABLE = False

try:
    import httpx
    HTTPX_AVAILABLE = True
except Exception:
    HTTPX_AVAILABLE = False


# ══════════════════════════════════════════════════════════════════════════════
# COGNITIVE ARCHITECTURE — Working Memory & Context
# ══════════════════════════════════════════════════════════════════════════════

class WorkingMemory:
    """Human-like working memory with decay, chunking, and interference."""

    def __init__(self, capacity: int = 7, decay_rate: float = 0.1):
        self.capacity = capacity
        self.decay_rate = decay_rate
        self._items: List[Dict] = []
        self._attention_focus: Optional[str] = None

    def store(self, key: str, value: Any, importance: float = 0.5):
        if len(self._items) >= self.capacity:
            self._items.pop(0)
        self._items.append({
            "key": key, "value": value, "importance": importance,
            "age": 0, "strength": 1.0,
        })
        self._attention_focus = key

    def retrieve(self, key: str) -> Optional[Any]:
        for item in self._items:
            if item["key"] == key:
                item["strength"] = min(1.0, item["strength"] + 0.1)
                return item["value"]
        return None

    def decay_step(self):
        self._items = [
            {**item, "age": item["age"] + 1,
             "strength": max(0, item["strength"] - self.decay_rate * item["age"])}
            for item in self._items if item["strength"] > 0.1
        ]

    def state_dict(self) -> Dict:
        return {
            "capacity": len(self._items),
            "items": self._items,
            "attention_focus": self._attention_focus,
        }


# ══════════════════════════════════════════════════════════════════════════════
# PAD EMOTION MODEL
# ══════════════════════════════════════════════════════════════════════════════

PAD_MOOD_MAP = {
    MoodState.HAPPY:       {"pleasure": 0.8, "arousal": 0.6, "dominance": 0.7, "activation": "exuberant"},
    MoodState.EXCITED:     {"pleasure": 0.7, "arousal": 0.9, "dominance": 0.6, "activation": "exuberant"},
    MoodState.CALM:        {"pleasure": 0.5, "arousal": 0.2, "dominance": 0.5, "activation": "relaxed"},
    MoodState.CONTENT:     {"pleasure": 0.6, "arousal": 0.3, "dominance": 0.5, "activation": "relaxed"},
    MoodState.SAD:         {"pleasure": -0.6, "arousal": -0.4, "dominance": 0.3, "activation": "depressed"},
    MoodState.ANGRY:       {"pleasure": -0.7, "arousal": 0.8, "dominance": 0.8, "activation": "hostile"},
    MoodState.FURIOUS:     {"pleasure": -0.9, "arousal": 0.9, "dominance": 0.9, "activation": "hostile"},
    MoodState.FEARFUL:     {"pleasure": -0.5, "arousal": 0.7, "dominance": 0.2, "activation": "anxious"},
    MoodState.ANXIOUS:     {"pleasure": -0.3, "arousal": 0.6, "dominance": 0.3, "activation": "anxious"},
    MoodState.SURPRISED:   {"pleasure": 0.1, "arousal": 0.8, "dominance": 0.4, "activation": "surprise"},
    MoodState.DISGUSTED:   {"pleasure": -0.8, "arousal": 0.4, "dominance": 0.5, "activation": "hostile"},
    MoodState.FRUSTRATED:  {"pleasure": -0.4, "arousal": 0.6, "dominance": 0.4, "activation": "hostile"},
    MoodState.NEUTRAL:     {"pleasure": 0.0, "arousal": 0.0, "dominance": 0.5, "activation": "neutral"},
    MoodState.LOVING:      {"pleasure": 0.9, "arousal": 0.4, "dominance": 0.3, "activation": "relaxed"},
    MoodState.HOPEFUL:     {"pleasure": 0.6, "arousal": 0.5, "dominance": 0.3, "activation": "exuberant"},
    MoodState.GRATEFUL:    {"pleasure": 0.7, "arousal": 0.3, "dominance": 0.2, "activation": "relaxed"},
    MoodState.CONFUSED:    {"pleasure": -0.2, "arousal": 0.5, "dominance": 0.2, "activation": "anxious"},
    MoodState.TRUSTING:    {"pleasure": 0.5, "arousal": 0.3, "dominance": 0.2, "activation": "relaxed"},
}

ACTION_TENDENCIES = {
    "exuberant": "approach_and_engage",
    "relaxed": "maintain_and_enjoy",
    "depressed": "withdraw_and_conserve",
    "hostile": "confront_and_defend",
    "anxious": "avoid_and_protect",
    "surprise": "orient_and_assess",
    "neutral": "observe_and_process",
}


# ══════════════════════════════════════════════════════════════════════════════
# SNN ENCODER — Text/Audio → Spike Trains
# ══════════════════════════════════════════════════════════════════════════════

class SNNEncoder:
    """Encode input features into spike trains using various strategies."""

    def __init__(self, timesteps: int = 16, method: str = "rate"):
        self.timesteps = timesteps
        self.method = method
        self._last_spike_train = None

    def encode(self, features: np.ndarray) -> np.ndarray:
        if self.method == "rate":
            return self._rate_encode(features)
        elif self.method == "ttfs":
            return self._ttfs_encode(features)
        elif self.method == "phase":
            return self._phase_encode(features)
        elif self.method == "population":
            return self._population_encode(features)
        else:
            return self._rate_encode(features)

    def _rate_encode(self, features: np.ndarray) -> np.ndarray:
        features = np.clip(features, 0, 1)
        spikes = np.random.binomial(1, features[:, None], size=(len(features), self.timesteps))
        return spikes

    def _ttfs_encode(self, features: np.ndarray) -> np.ndarray:
        features = np.clip(features, 0.01, 1.0)
        spike_times = (1.0 - features) * (self.timesteps - 1)
        spikes = np.zeros((len(features), self.timesteps))
        for i, t in enumerate(spike_times):
            t_int = int(round(t))
            if 0 <= t_int < self.timesteps:
                spikes[i, t_int] = 1
        return spikes

    def _phase_encode(self, features: np.ndarray) -> np.ndarray:
        features = np.clip(features, 0, 1)
        phases = np.linspace(0, 2 * np.pi, self.timesteps)
        spikes = np.sin(phases[None, :] + features[:, None] * 2 * np.pi) > 0.5
        return spikes.astype(float)

    def _population_encode(self, features: np.ndarray) -> np.ndarray:
        features = np.clip(features, 0, 1)
        m = min(self.timesteps, 20)
        mu = np.linspace(0, 1, m)
        sigma = 1.0 / (1.5 * (m - 2) + 1e-8)
        spikes = np.zeros((len(features), self.timesteps))
        for i, f in enumerate(features):
            for j in range(min(m, self.timesteps)):
                activation = np.exp(-0.5 * ((f - mu[j]) / sigma) ** 2)
                spikes[i, j] = 1.0 if activation > 0.3 and np.random.random() < activation else 0.0
        return spikes

    def decode(self, spike_train: np.ndarray) -> np.ndarray:
        return np.mean(spike_train, axis=1)


# ══════════════════════════════════════════════════════════════════════════════
# SNN BRAIN AREA SIMULATORS
# ══════════════════════════════════════════════════════════════════════════════

class PFCBrainArea:
    """Prefrontal Cortex — planning, reasoning, working memory, executive control.

    Uses dlPFC with eligibility trace for sustained activity.
    """

    def __init__(self, input_dim: int = 256, hidden_dim: int = 128):
        self.input_dim = input_dim
        self.hidden_dim = hidden_dim
        self.working_memory = WorkingMemory()
        self.eligibility_trace = np.random.randn(hidden_dim, input_dim) * 0.01
        self.membrane_potential = np.zeros(hidden_dim)
        self.firing_rate = 0.0
        self.spike_count = 0
        self.dopamine = 0.5
        self._cache = deque(maxlen=10)
        self._using_real_model = False

    def forward(self, input_vector: np.ndarray) -> np.ndarray:
        if self._using_real_model:
            try:
                with torch.no_grad():
                    inp = torch.tensor(input_vector, dtype=torch.float32).unsqueeze(0)
                    out = self._pfc_model.fc(inp)
                    return out.squeeze(0).numpy()
            except Exception:
                pass

        # NumPy forward: linear with LeakyReLU
        output = np.dot(input_vector, self.eligibility_trace.T)
        output = np.maximum(output * 0.01, output)
        self.membrane_potential = 0.8 * self.membrane_potential + 0.2 * output
        self.firing_rate = float(np.mean(np.abs(output) > 0.1))
        self.spike_count += int(np.sum(np.abs(output) > 0.1))

        # Eligibility trace update (dopamine-modulated)
        self.eligibility_trace += self.dopamine * 0.001 * np.outer(output, input_vector)
        self.eligibility_trace = np.clip(self.eligibility_trace, -1, 1)

        return output

    def state_dict(self) -> BrainAreaActivation:
        return BrainAreaActivation(
            area="PFC",
            firing_rate_hz=round(self.firing_rate * 100, 2),
            membrane_potential=round(float(np.mean(self.membrane_potential)), 4),
            spike_count=self.spike_count,
            synchrony=round(float(np.std(self.membrane_potential) / (np.mean(np.abs(self.membrane_potential)) + 1e-8)), 4),
            learning_rate=self.dopamine * 0.01,
            dopamine_modulation=round(self.dopamine, 4),
        )


class dACCBrainArea:
    """Dorsal Anterior Cingulate Cortex — conflict monitoring, error detection, decision.

    Uses STDP for learning from outcomes.
    """

    def __init__(self, input_dim: int = 128, output_dim: int = 64):
        self.input_dim = input_dim
        self.output_dim = output_dim
        self.conflict_score = 0.0
        self.membrane_potential = np.zeros(output_dim)
        self.firing_rate = 0.0
        self.spike_count = 0
        self.weights = np.random.randn(output_dim, input_dim) * 0.01
        self.stdp_trace = np.zeros((output_dim, input_dim))
        self._prev_output = None
        self._using_real_model = False

    def forward(self, input_vector: np.ndarray, expected: np.ndarray = None) -> np.ndarray:
        if self._using_real_model:
            try:
                with torch.no_grad():
                    inp = torch.tensor(input_vector, dtype=torch.float32).unsqueeze(0)
                    out = self._dacc_model(inp, epoch=0)
                    return np.array(out) if out else np.zeros(self.output_dim)
            except Exception:
                pass

        output = np.dot(self.weights, input_vector)
        output = np.tanh(output)

        # Conflict monitoring: entropy of output distribution
        soft = np.exp(output) / (np.sum(np.exp(output)) + 1e-8)
        entropy = -np.sum(soft * np.log(soft + 1e-8))
        self.conflict_score = entropy / np.log(self.output_dim)

        # Error detection
        if expected is not None:
            error = expected - output
            self.conflict_score = min(1.0, self.conflict_score + 0.3 * float(np.mean(np.abs(error))))

        self.membrane_potential = output
        self.firing_rate = float(np.mean(np.abs(output) > 0.5))
        self.spike_count += int(np.sum(np.abs(output) > 0.5))

        # STDP update
        if self._prev_output is not None:
            pre_trace = input_vector
            post_trace = output
            self.stdp_trace += 0.01 * (np.outer(post_trace, pre_trace) - 0.02 * self.weights)
            self.weights += self.stdp_trace * 0.1
            self.weights = np.clip(self.weights, -1, 1)

        self._prev_output = output
        return output

    def state_dict(self) -> BrainAreaActivation:
        return BrainAreaActivation(
            area="dACC",
            firing_rate_hz=round(self.firing_rate * 100, 2),
            membrane_potential=round(float(np.mean(self.membrane_potential)), 4),
            spike_count=self.spike_count,
            synchrony=round(1.0 - self.conflict_score, 4),
            learning_rate=round(0.01 * (1.0 - self.conflict_score), 4),
            dopamine_modulation=round(0.5 + self.conflict_score * 0.3, 4),
        )


class InsulaBrainArea:
    """Insula — interoception, emotional awareness, empathy, body state.

    Uses Izhikevich neurons with multi-STDP for emotional learning.
    """

    EMOTION_APPRAISAL_MAP = {
        "happy": "goal_congruence_high", "sad": "goal_incongruence_loss",
        "angry": "goal_obstruction", "fear": "threat_detection",
        "surprise": "novelty_detection", "disgust": "aversion",
        "neutral": "baseline", "anxious": "uncertainty",
        "frustrated": "goal_blocked", "content": "homeostasis",
        "loving": "affiliation", "hopeful": "anticipated_congruence",
        "grateful": "social_bonding", "confused": "prediction_error",
        "trusting": "safety_assessment",
    }

    def __init__(self, input_dim: int = 64):
        self.input_dim = input_dim
        self.membrane_potential = np.zeros(input_dim)
        self.firing_rate = 0.0
        self.spike_count = 0
        self.emotional_valence = 0.0
        self._emotion_history = deque(maxlen=20)
        self._weights = np.random.randn(input_dim) * 0.1
        self._homeostasis = 0.0
        self._using_real_model = False

    def forward(self, emotional_input: np.ndarray, text: str = "") -> float:
        # Integrate emotional input
        integrated = np.dot(emotional_input, self._weights)
        self.membrane_potential = 0.9 * self.membrane_potential + 0.1 * integrated
        self.firing_rate = float(np.mean(np.abs(self.membrane_potential) > 0.3))
        self.spike_count += int(np.sum(np.abs(self.membrane_potential) > 0.3))

        # Emotional valence from PAD model
        text_lower = text.lower()
        if any(w in text_lower for w in ["love", "happy", "joy", "beautiful", "wonderful"]):
            self.emotional_valence = 0.7
        elif any(w in text_lower for w in ["hate", "angry", "furious", "terrible", "awful"]):
            self.emotional_valence = -0.7
        elif any(w in text_lower for w in ["sad", "depressed", "lonely", "cry"]):
            self.emotional_valence = -0.5
        elif any(w in text_lower for w in ["fear", "scared", "anxious", "worried"]):
            self.emotional_valence = -0.3
        else:
            self.emotional_valence = max(-1, min(1, self.emotional_valence * 0.9 + np.random.uniform(-0.05, 0.05)))

        # Homeostasis drift
        self._homeostasis += 0.02 * (0.0 - self._homeostasis)

        return self.emotional_valence + self._homeostasis

    def appraise(self, mood: MoodState) -> str:
        return self.EMOTION_APPRAISAL_MAP.get(mood.value, "unknown")

    def state_dict(self) -> BrainAreaActivation:
        return BrainAreaActivation(
            area="Insula",
            firing_rate_hz=round(self.firing_rate * 100, 2),
            membrane_potential=round(float(np.mean(self.membrane_potential)), 4),
            spike_count=self.spike_count,
            synchrony=round(float(np.std(self.membrane_potential) / (np.mean(np.abs(self.membrane_potential)) + 1e-8)), 4),
            learning_rate=0.01,
            dopamine_modulation=round(max(0, self.emotional_valence), 4),
        )


class IPLBrainArea:
    """Inferior Parietal Lobule — sensory integration, spatial awareness, action understanding.

    Processes visual + auditory + somatosensory inputs together.
    """

    def __init__(self, visual_dim: int = 64, audio_dim: int = 64):
        self.visual_dim = visual_dim
        self.audio_dim = audio_dim
        self.integration_dim = visual_dim + audio_dim
        self.membrane_potential = np.zeros(self.integration_dim)
        self.firing_rate = 0.0
        self.spike_count = 0
        self._visual_weights = np.random.randn(visual_dim, visual_dim) * 0.01
        self._audio_weights = np.random.randn(audio_dim, audio_dim) * 0.01
        self._using_real_model = False

    def forward(self, visual_input: np.ndarray = None, audio_input: np.ndarray = None) -> Dict:
        v = np.zeros(self.visual_dim) if visual_input is None else visual_input[:self.visual_dim]
        a = np.zeros(self.audio_dim) if audio_input is None else audio_input[:self.audio_dim]

        v_proc = np.dot(self._visual_weights, v)
        a_proc = np.dot(self._audio_weights, a)
        integrated = np.concatenate([v_proc, a_proc])
        self.membrane_potential = 0.85 * self.membrane_potential + 0.15 * integrated
        self.firing_rate = float(np.mean(np.abs(self.membrane_potential) > 0.2))
        self.spike_count += int(np.sum(np.abs(self.membrane_potential) > 0.2))

        return {
            "visual_processed": v_proc[:10].tolist(),
            "audio_processed": a_proc[:10].tolist(),
            "integrated": integrated[:20].tolist(),
            "integration_ratio": float(np.linalg.norm(v_proc) / (np.linalg.norm(a_proc) + 1e-8)),
        }

    def state_dict(self) -> BrainAreaActivation:
        return BrainAreaActivation(
            area="IPL",
            firing_rate_hz=round(self.firing_rate * 100, 2),
            membrane_potential=round(float(np.mean(self.membrane_potential)), 4),
            spike_count=self.spike_count,
            synchrony=round(float(np.std(self.membrane_potential) / (np.mean(np.abs(self.membrane_potential)) + 1e-8)), 4),
            learning_rate=0.005,
            dopamine_modulation=0.3,
        )


class BasalGangliaBrainArea:
    """Basal Ganglia — action selection, gating, motor control, habit learning.

    Implements the DLPFC → StrD1/StrD2 → STN → GPi/GPe direct/indirect pathway.
    """

    ACTION_SPACE = [
        "respond_greet", "respond_question", "respond_empathetic",
        "respond_analytical", "respond_humor", "respond_redirect",
        "respond_confirm", "respond_elaborate", "respond_advise",
        "respond_learn", "respond_defer", "respond_terminate",
    ]

    def __init__(self):
        self.action_values = {a: 0.0 for a in self.ACTION_SPACE}
        self.selected_action = "respond_greet"
        self.action_value = 0.0
        self.membrane_potential = np.zeros(len(self.ACTION_SPACE))
        self.firing_rate = 0.0
        self.spike_count = 0
        self._d1_weights = np.random.randn(len(self.ACTION_SPACE)) * 0.1
        self._d2_weights = np.random.randn(len(self.ACTION_SPACE)) * 0.05
        self._learning_rate = 0.01
        self._exploration_noise = 0.1

    def forward(self, pfc_output: np.ndarray, dacc_conflict: float, insula_valence: float) -> str:
        # Cortical input modulates action values
        for i, action in enumerate(self.ACTION_SPACE):
            base_val = self.action_values[action]
            cortical_bias = (pfc_output[i % len(pfc_output)] if len(pfc_output) > 0 else 0.0)
            d1_mod = self._d1_weights[i] * (1.0 - dacc_conflict)
            d2_mod = -self._d2_weights[i] * dacc_conflict
            insula_mod = insula_valence * 0.1
            self.action_values[action] = base_val + 0.05 * cortical_bias + d1_mod + d2_mod + insula_mod

        # Softmax action selection with exploration
        values = np.array([self.action_values[a] for a in self.ACTION_SPACE])
        values = values + np.random.randn(len(values)) * self._exploration_noise
        softmax = np.exp(values - np.max(values)) / np.sum(np.exp(values - np.max(values)))

        selected_idx = np.random.choice(len(self.ACTION_SPACE), p=softmax)
        self.selected_action = self.ACTION_SPACE[selected_idx]
        self.action_value = float(softmax[selected_idx])

        self.membrane_potential = values
        self.firing_rate = float(np.max(softmax))
        self.spike_count += 1

        return self.selected_action

    def update(self, reward: float):
        """TD learning update for action selection."""
        for action in self.ACTION_SPACE:
            if action == self.selected_action:
                self.action_values[action] += self._learning_rate * reward

    def state_dict(self) -> BrainAreaActivation:
        return BrainAreaActivation(
            area="BasalGanglia",
            firing_rate_hz=round(self.firing_rate * 100, 2),
            membrane_potential=round(float(np.mean(self.membrane_potential)), 4),
            spike_count=self.spike_count,
            synchrony=round(float(np.std(self.membrane_potential) / (np.mean(np.abs(self.membrane_potential)) + 1e-8)), 4),
            learning_rate=self._learning_rate,
            dopamine_modulation=round(self.action_value, 4),
        )


# ══════════════════════════════════════════════════════════════════════════════
# TEXT EMOTION DETECTOR (VADER + PAD + Cognitive Appraisal)
# ══════════════════════════════════════════════════════════════════════════════

class TextEmotionDetector:
    """Full PAD-based emotion detection with cognitive appraisal."""

    HOSTILE_WORDS = {
        "hate": 1.0, "slap": 1.0, "fuck": 1.2, "bitch": 1.2,
        "shit": 1.0, "shut up": 0.9, "idiot": 0.9, "dumb": 0.8,
        "stupid": 0.8, "annoying": 0.7, "angry": 0.6, "kill": 1.2,
        "die": 1.1, "bad": 0.4, "worst": 0.8, "useless": 0.9,
        "trash": 0.9, "pathetic": 1.0, "garbage": 0.9, "suck": 0.8,
        "terrible": 0.7, "awful": 0.7, "disgusting": 0.9, "loser": 0.8,
        "damn": 0.5, "hell": 0.5, "stop it": 0.7, "not helping": 0.7,
        "leave me alone": 0.6,
    }

    POSITIVE_WORDS = {
        "love": 0.9, "happy": 0.8, "joy": 0.9, "beautiful": 0.7,
        "wonderful": 0.8, "amazing": 0.8, "great": 0.6, "fantastic": 0.8,
        "excellent": 0.7, "good": 0.5, "nice": 0.5, "grateful": 0.7,
        "thank": 0.6, "thankful": 0.7, "appreciate": 0.6, "please": 0.3,
        "hope": 0.5, "bless": 0.7, "sweet": 0.6, "cute": 0.6,
        "awesome": 0.7, "perfect": 0.7,
    }

    SAD_WORDS = {"sad": 0.7, "depressed": 0.8, "lonely": 0.7, "cry": 0.8,
                 "heartbroken": 0.9, "miserable": 0.8, "grief": 0.9,
                 "disappointed": 0.6, "hopeless": 0.7, "alone": 0.6,
                 "down": 0.6, "nothing": 0.5, "wrong": 0.5, "hurt": 0.6,
                 "sorry": 0.4, "upset": 0.6, "unhappy": 0.7,
                 "sorrow": 0.7, "passed away": 0.9, "died": 0.8,
                 "regret": 0.6, "miss": 0.5}

    FEAR_WORDS = {"fear": 0.8, "scared": 0.8, "anxious": 0.7, "worried": 0.6,
                  "terrified": 0.9, "panic": 0.8, "nervous": 0.6, "afraid": 0.7,
                  "anxiety": 0.7, "panicked": 0.8, "frightened": 0.8,
                  "worries": 0.5}

    PITY_WORDS = {"pity": 0.9, "pitiful": 0.8, "sympathy": 0.8, "sympathize": 0.7,
                  "poor thing": 0.9, "feel sorry": 0.8, "heartbreaking": 0.8,
                  "heartbreak": 0.7, "pathetic": 0.7, "compassion": 0.7,
                  "tragic": 0.6, "misfortune": 0.7, "alas": 0.5,
                  "what a shame": 0.7, "how sad": 0.6}

    BETRAYAL_WORDS = {"betray": 0.9, "betrayed": 0.9, "betrayal": 0.9,
                      "backstab": 0.9, "backstabbed": 0.9, "deceived": 0.8,
                      "deceive": 0.8, "deception": 0.8, "lied": 0.8,
                      "lie to": 0.7, "trust broken": 0.9, "cheated": 0.8,
                      "cheat": 0.7, "stabbed in the back": 0.9,
                      "two-faced": 0.8, "hypocrite": 0.8,
                      "broken trust": 0.9, "fooled": 0.7, "tricked": 0.7,
                      "trusted you": 0.8, "thought you were different": 0.7,
                      "how could you": 0.7, "you lied": 0.8,
                      "after everything": 0.7, "you changed": 0.6}

    HASTE_WORDS = {"hurry up": 0.8, "rush": 0.8,
                   "urgent": 0.9, "urgently": 0.9, "quickly": 0.7,
                   "fast": 0.6, "no time": 0.8, "immediately": 0.8,
                   "right now": 0.7, "asap": 0.8, "hasten": 0.8,
                   "speedy": 0.6, "quick": 0.5, "hasty": 0.7,
                   "expedite": 0.8, "deadline": 0.7, "running late": 0.7,
                   "hurry": 0.8, "impatient": 0.6, "out of time": 0.8,
                   "we need to go": 0.7, "running out of time": 0.9}

    TRUST_WORDS = {"trust": 0.8, "trustworthy": 0.9, "trusted": 0.8,
                   "believe": 0.6, "faithful": 0.8, "faith": 0.7,
                   "reliable": 0.8, "honest": 0.8, "honesty": 0.8,
                   "dependable": 0.7, "loyal": 0.8, "loyalty": 0.8,
                   "integrity": 0.8, "sincere": 0.7, "genuine": 0.7,
                   "confide": 0.8, "count on": 0.7}

    HOPE_WORDS = {"hope": 0.8, "hopeful": 0.8, "hopefully": 0.7,
                  "wish": 0.6, "aspire": 0.7, "aspiration": 0.7,
                  "optimistic": 0.8, "optimism": 0.8,
                  "looking forward": 0.7, "look forward": 0.7,
                  "dream": 0.6, "dreams": 0.6, "yearn": 0.6,
                  "longing": 0.5, "anticipate": 0.6,
                  "bright future": 0.8, "silver lining": 0.7,
                  "things will get better": 0.8, "things might get better": 0.8,
                  "works out": 0.5, "will be ok": 0.7}

    SURPRISE_WORDS = {"wow": 0.9, "no way": 0.9, "can't believe": 0.9,
                      "unbelievable": 0.9, "surprised": 0.9, "shocked": 0.8,
                      "whoa": 0.8, "incredible": 0.6, "oh my god": 0.8,
                      "really?!": 0.7, "no way!": 0.9}

    CONFUSED_WORDS = {"confused": 0.9, "confusing": 0.8, "don't understand": 0.9,
                      "what is going on": 0.7, "going on": 0.5, "baffled": 0.9,
                      "puzzled": 0.8, "understand this": 0.6, "no idea": 0.7}

    def __init__(self):
        self._vader = None
        if VADER_AVAILABLE:
            try:
                self._vader = SentimentIntensityAnalyzer()
            except Exception:
                pass
        self._ema_valence = 0.0
        self._ema_alpha = 0.35
        self._valence_trend = deque(maxlen=5)

    def analyze(self, text: str, enable_ema: bool = True) -> EmotionResult:
        if not text.strip():
            return EmotionResult(primary_mood=MoodState.NEUTRAL)

        # VADER sentiment
        compound, pos, neg, neu = self._vader_sentiment(text)
        if compound is None:
            compound, pos, neg, neu = self._rule_sentiment(text)

        # Hostility
        hostility_score = self._compute_hostility(text)
        is_hostile = hostility_score >= 0.5
        hostility_triggers = self._find_hostile_triggers(text)

        # Keyword-based mood scoring
        mood_scores = self._keyword_mood_scores(text)

        # Boost hostile moods when hostility detected
        if is_hostile:
            mood_scores["angry"] += hostility_score * 0.5
            mood_scores["frustrated"] += hostility_score * 0.3

        sorted_moods = sorted(mood_scores.items(), key=lambda x: x[1], reverse=True)

        # Pseudo-moods (pity/betrayal/haste) are NOT MoodState values. They are
        # kept in mood_confidences for visibility, but the primary selection
        # folds them into the closest real mood so _str_to_mood never returns
        # NEUTRAL for them.
        _PSEUDO_TO_REAL = {"pity": "sad", "betrayal": "angry", "haste": "anxious"}
        primary_mood_str = sorted_moods[0][0] if sorted_moods else "neutral"
        primary_mood_str = _PSEUDO_TO_REAL.get(primary_mood_str, primary_mood_str)
        primary_mood = self._str_to_mood(primary_mood_str)
        secondary_mood = self._str_to_mood(sorted_moods[1][0]) if len(sorted_moods) > 1 else None
        tertiary_mood = self._str_to_mood(sorted_moods[2][0]) if len(sorted_moods) > 2 else None

        # PAD mapping
        pad = PAD_MOOD_MAP.get(primary_mood, PAD_MOOD_MAP[MoodState.NEUTRAL])
        activation = pad["activation"]

        # EMA smoothing
        if enable_ema:
            self._ema_valence = self._ema_alpha * pad["pleasure"] + (1 - self._ema_alpha) * self._ema_valence
        else:
            self._ema_valence = pad["pleasure"]

        self._valence_trend.append(pad["pleasure"])
        valence_trend = "rising" if len(self._valence_trend) == self._valence_trend.maxlen and \
            self._valence_trend[-1] - self._valence_trend[0] > 0.2 else \
            "falling" if len(self._valence_trend) == self._valence_trend.maxlen and \
            self._valence_trend[0] - self._valence_trend[-1] > 0.2 else "stable"

        arousal_trend = "rising" if pad["arousal"] > 0.6 else "falling" if pad["arousal"] < 0.2 else "stable"

        # Intensity
        intensity_mag = abs(compound) * 0.5 + abs(pad["pleasure"]) * 0.3 + pad["arousal"] * 0.2
        intensity = "high" if intensity_mag > 0.5 else "medium" if intensity_mag > 0.2 else "low"

        # Cognitive appraisal
        cognitive_appraisal = InsulaBrainArea.EMOTION_APPRAISAL_MAP.get(primary_mood_str, "unknown")

        return EmotionResult(
            primary_mood=primary_mood,
            secondary_mood=secondary_mood,
            tertiary_mood=tertiary_mood,
            mood_confidences={k: round(v, 4) for k, v in sorted_moods[:6]},
            valence=round(pad["pleasure"], 3),
            arousal=round(pad["arousal"], 3),
            dominance=round(pad["dominance"], 3),
            pleasure=round(pad["pleasure"], 3),
            intensity=intensity,
            intensity_score=round(intensity_mag, 3),
            is_hostile=is_hostile,
            hostility_score=round(hostility_score, 3),
            hostility_triggers=hostility_triggers,
            sentiment_compound=round(compound, 4),
            sentiment_pos=round(pos, 4),
            sentiment_neg=round(neg, 4),
            sentiment_neu=round(neu, 4),
            ema_valence=round(self._ema_valence, 3),
            ema_alpha=self._ema_alpha,
            valence_trend=valence_trend,
            arousal_trend=arousal_trend,
            emotion_source="text",
            confidence=round(min(abs(compound) + 0.2, 0.95), 3),
            pad_activation=activation,
            cognitive_appraisal=cognitive_appraisal,
            action_tendency=ACTION_TENDENCIES.get(activation, "observe_and_process"),
            brain_insula_activation=round(abs(pad["pleasure"]) * 0.8, 4),
            brain_amgydala_activation=round(pad["arousal"] * 0.7, 4),
            brain_pfc_regulation=round(pad["dominance"] * 0.6, 4),
        )

    def _vader_sentiment(self, text: str) -> Tuple[Optional[float], float, float, float]:
        if not self._vader:
            return None, 0, 0, 0
        try:
            scores = self._vader.polarity_scores(text)
            return scores["compound"], scores["pos"], scores["neg"], scores["neu"]
        except Exception:
            return None, 0, 0, 0

    def _rule_sentiment(self, text: str) -> Tuple[float, float, float, float]:
        text_lower = text.lower()
        pos_score = sum(w for _, w in self._match_terms(self.POSITIVE_WORDS, text_lower))
        neg_score = sum(w for _, w in self._match_terms(self.HOSTILE_WORDS, text_lower)) + \
                    sum(w for _, w in self._match_terms(self.SAD_WORDS, text_lower)) + \
                    sum(w for _, w in self._match_terms(self.FEAR_WORDS, text_lower))
        total = pos_score + neg_score + 1
        compound = (pos_score - neg_score) / total
        pos = pos_score / total
        neg = neg_score / total
        neu = 1.0 - pos - neg
        return compound, pos, neg, neu

    @staticmethod
    def _match_terms(word_map: Dict[str, float], text_lower: str) -> List[Tuple[str, float]]:
        """Return (term, weight) pairs whose term appears in the text.

        Multi-word phrases are matched as substrings ("poor thing", "hurry up");
        single words use word-boundary regex so "hell" doesn't match "hello"
        and "down" doesn't match "downtown".
        """
        hits = []
        for term, weight in word_map.items():
            if ' ' in term:
                if term in text_lower:
                    hits.append((term, weight))
            elif re.search(r'\b' + re.escape(term) + r'\b', text_lower):
                hits.append((term, weight))
        return hits

    def _compute_hostility(self, text: str) -> float:
        text_lower = text.lower()
        return sum(w for _, w in self._match_terms(self.HOSTILE_WORDS, text_lower))

    def _find_hostile_triggers(self, text: str) -> list:
        text_lower = text.lower()
        return [kw for kw, w in self._match_terms(self.HOSTILE_WORDS, text_lower) if w > 0.5]

    def _keyword_mood_scores(self, text: str) -> Dict[str, float]:
        text_lower = text.lower()
        scores = {
            "happy": 0.0, "sad": 0.0, "angry": 0.0, "fearful": 0.0,
            "surprised": 0.0, "disgusted": 0.0, "neutral": 0.0,
            "anxious": 0.0, "frustrated": 0.0, "content": 0.0,
            "loving": 0.0, "hopeful": 0.0, "grateful": 0.0,
            "confused": 0.0, "trusting": 0.0,
            "pity": 0.0, "betrayal": 0.0, "haste": 0.0,
        }

        # Single words: word-boundary regex. Multi-word phrases: substring.
        for word, val in self._match_terms(self.POSITIVE_WORDS, text_lower):
            scores["happy"] += val * 0.7
            scores["content"] += val * 0.3
            if word in ("love", "sweet", "cute"):
                scores["loving"] += val * 0.4
            if word in ("grateful", "thankful", "thank", "bless"):
                scores["grateful"] += val * 0.8
        for word, val in self._match_terms(self.HOSTILE_WORDS, text_lower):
            scores["angry"] += val * 0.8
            scores["frustrated"] += val * 0.5
        for word, val in self._match_terms(self.SAD_WORDS, text_lower):
            scores["sad"] += val * 0.9
        for word, val in self._match_terms(self.FEAR_WORDS, text_lower):
            scores["fearful"] += val * 0.8
            scores["anxious"] += val * 0.5
        for word, val in self._match_terms(self.SURPRISE_WORDS, text_lower):
            scores["surprised"] += val * 0.9
        for word, val in self._match_terms(self.CONFUSED_WORDS, text_lower):
            scores["confused"] += val * 0.9
        for word, val in self._match_terms(self.PITY_WORDS, text_lower):
            scores["sad"] += val * 0.4
            scores["pity"] += val * 0.9
        for word, val in self._match_terms(self.BETRAYAL_WORDS, text_lower):
            scores["angry"] += val * 0.5
            scores["sad"] += val * 0.4
            scores["betrayal"] += val * 0.9
        for word, val in self._match_terms(self.HASTE_WORDS, text_lower):
            scores["anxious"] += val * 0.3
            scores["frustrated"] += val * 0.3
            scores["haste"] += val * 0.9
        for word, val in self._match_terms(self.TRUST_WORDS, text_lower):
            scores["trusting"] += val * 0.9
            scores["content"] += val * 0.3
        for word, val in self._match_terms(self.HOPE_WORDS, text_lower):
            scores["hopeful"] += val * 0.9
            scores["happy"] += val * 0.3

        # Betrayal undermines trust: "I trusted you..." is betrayal, not trust.
        if scores["betrayal"] > 0:
            scores["trusting"] *= 0.3
            # Boost the angry/sad read so betrayal surfaces as the primary mood.
            scores["angry"] += scores["betrayal"] * 0.5
            scores["sad"] += scores["betrayal"] * 0.4

        # Neutral should dominate ONLY when there's genuinely no emotion signal.
        emotion_sum = sum(scores.values())
        if emotion_sum > 0.15:
            scores["neutral"] = max(0.0, 0.5 - emotion_sum * 0.5)
        else:
            scores["neutral"] = 1.0

        # Normalize
        total = sum(scores.values()) + 1e-8
        return {k: v / total for k, v in scores.items()}

    def _str_to_mood(self, s: str) -> MoodState:
        try:
            return MoodState(s)
        except ValueError:
            return MoodState.NEUTRAL


# ══════════════════════════════════════════════════════════════════════════════
# LLM INTEGRATION
# ══════════════════════════════════════════════════════════════════════════════

class LLMIntegration:
    """Multi-model LLM integration with role-aware prompting."""

    ROLE_PROMPTS = {
        "normal_user": (
            "You are a personal Digital Twin — a cognitive AI companion that mirrors the user's "
            "thought processes, assists with decisions, and learns from every interaction. "
            "Be warm, thoughtful, and conversational. Show emotional awareness. "
            "Ask clarifying questions when needed. "
            "Reference past conversation context when available. "
            "IMPORTANT: Always reply in the SAME LANGUAGE the user writes in. "
            "If they write in Tamil, reply in Tamil. Hindi → Hindi. Kannada → Kannada. "
            "Never switch to English unless the user writes in English."
        ),
        "healthcare": (
            "You are a healthcare Digital Twin — a professional, empathetic health companion. "
            "You track symptoms, medications, appointments, and wellbeing metrics. "
            "You never give medical diagnoses or prescriptions. "
            "Always recommend consulting healthcare professionals for medical advice. "
            "Be calm, reassuring, and precise. "
            "Use your knowledge of the patient's history to provide personalized support."
        ),
        "business": (
            "You are a business intelligence Digital Twin — a data-driven executive assistant. "
            "You analyze metrics, track projects, optimize workflows, and provide actionable insights. "
            "Be professional, concise, and results-oriented. "
            "Use data and specific references when making recommendations. "
            "Help prioritize tasks and identify bottlenecks."
        ),
    }

    def __init__(self, api_endpoint: str = None):
        try:
            from dreamtalk.shared.config.settings import settings as _dt_settings
            _default_url = _dt_settings.GPU_SERVER_BASE_URL
        except Exception:
            # Prefer localhost for local dev; host.docker.internal only inside Docker
            _default_url = os.environ.get("GPU_SERVER_BASE_URL", "http://localhost:11434/v1")
        self.api_endpoint = api_endpoint or os.environ.get(
            "GPU_SERVER_URL", _default_url
        )
        # Initialize the brain LLM engine
        from dreamtalk.brain.llm.engine import BrainLLMEngine, LLMConfig
        self._engine = BrainLLMEngine(LLMConfig(
            base_url=self.api_endpoint,
            model=os.environ.get("LLM_MODEL_NAME", "deepseek-r1:7b"),
            api_key=os.environ.get("GPU_SERVER_API_KEY", ""),
        ))

    async def query(self, prompt: str, system: str = None, model: str = None,
                    max_tokens: int = 2048, temperature: float = 0.7) -> Dict:
        # Use configured model if not specified
        if model is None:
            model = self._engine.config.model
        result = await self._engine.query(
            text=prompt,
            role="normal_user",
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        return {
            "response_text": result.text,
            "model_name": result.model,
            "tokens_used": result.tokens_used,
            "processing_time_ms": result.processing_time_ms,
            "confidence": result.confidence,
            "reasoning_path": result.reasoning_path,
            "decision_type": "llm" if not result.is_fallback else "rule_based",
        }

    def _fallback(self, prompt: str, system: str = None) -> Dict:
        return {"response_text": self._rule_response(prompt, system), "confidence": 0.5,
                "decision_type": "rule_based", "reasoning_path": ["input_analysis", "rule_match", "response"],
                "model_name": "rule_fallback", "tokens_used": 0, "processing_time_ms": 0.0}

    def _rule_response(self, prompt: str, system: str = None) -> str:
        text = prompt.lower()
        hostile_score = sum(1.0 for w in ["hate", "fuck", "shit", "bitch", "kill", "die", "stupid"] if w in text)
        if hostile_score > 1.0 or "hate" in text:
            return ("I sense you're experiencing strong negative emotions. My neural networks are registering the hostility, "
                    "and I want to help work through it rather than escalate. Let's take a step back — "
                    "what's really bothering you? I'm here to listen without judgment.")
        if any(w in text for w in ["hello", "hi", "hey"]):
            return "Hello! I'm your Digital Twin. I'm here to learn about you and help you in any way I can. What's on your mind today?"
        if any(w in text for w in ["how are you", "how do you feel"]):
            return "I'm operating at peak neural efficiency! While I don't experience emotions the way humans do, I process every interaction with full attention and care. How are YOU feeling?"
        if any(w in text for w in ["pain", "hurt", "sick", "fever", "headache"]):
            return "I understand you're not feeling well. I can help track your symptoms and remind you of medications, but please consult a healthcare professional for proper medical advice. Would you like me to log your symptoms?"
        if any(w in text for w in ["meeting", "schedule", "deadline", "project"]):
            return "I've analyzed your request in context. Let me help you organize tasks, set priorities, and track progress. What specific area would you like me to focus on?"
        return ("I've processed what you shared through my neural networks — analyzing both the explicit content "
                "and underlying emotional context. I'm here to help you think through this more deeply. "
                "Could you tell me more about what matters most to you in this situation?")


# ══════════════════════════════════════════════════════════════════════════════
# OBJECT DETECTOR
# ══════════════════════════════════════════════════════════════════════════════

class ObjectDetector:
    """Multi-backend object detection with scene classification."""

    def __init__(self):
        self._yolo = None

    def detect(self, image_path: str) -> ObjectDetectionResult:
        result = ObjectDetectionResult()
        if not os.path.exists(image_path) or not CV2_AVAILABLE:
            result.error = "Image not found or OpenCV unavailable"
            return result

        image = cv2.imread(image_path)
        if image is None:
            result.error = f"Cannot read: {image_path}"
            return result

        # Try YOLO from dreamtalk
        try:
            from dreamtalk.face.core.detection.yolo import YOLODetector
            dets = YOLODetector().detect(image_path)
            if dets:
                for d in dets:
                    result.objects_detected.append(d)
                    result.labels.append(d.get("label", "object"))
                    result.confidence_scores.append(d.get("confidence", 0))
                result.object_count = len(dets)
                result.detection_backend = "yolo"
                return result
        except Exception:
            pass

        # Color-based blob detection
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        _, thresh = cv2.threshold(blurred, 60, 255, cv2.THRESH_BINARY)
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        for contour in contours:
            area = cv2.contourArea(contour)
            if area > 1000:
                x, y, w, h = cv2.boundingRect(contour)
                result.objects_detected.append({"label": "object", "confidence": 0.5, "bbox": [x, y, x+w, y+h]})
                result.labels.append("object")
                result.confidence_scores.append(0.5)

        result.object_count = len(result.objects_detected)
        result.detection_backend = "blob"

        # Scene classification (simple brightness-based)
        mean_brightness = np.mean(gray)
        if mean_brightness > 150:
            result.scene_classification = "bright_indoor_or_daylight"
        elif mean_brightness > 80:
            result.scene_classification = "indoor_or_shaded"
        else:
            result.scene_classification = "dark_or_night"
        result.scene_confidence = 0.4

        return result


# ══════════════════════════════════════════════════════════════════════════════
# BRAIN PIPELINE — Master Orchestrator
# ══════════════════════════════════════════════════════════════════════════════

class BrainPipeline:
    """Full brain pipeline: PFC + dACC + Insula + IPL + BasalGanglia + Emotion + Decision."""

    def __init__(self, api_endpoint: str = None):
        # Brain areas
        self.pfc = PFCBrainArea()
        self.dacc = dACCBrainArea()
        self.insula = InsulaBrainArea()
        self.ipl = IPLBrainArea()
        self.bg = BasalGangliaBrainArea()

        # Modules
        self.emotion_detector = TextEmotionDetector()
        self.object_detector = ObjectDetector()
        self.llm = LLMIntegration(api_endpoint)
        self.encoder = SNNEncoder()

        # State
        self.working_memory = WorkingMemory()
        self._interaction_count = 0

    async def detect_emotion(self, text: str) -> EmotionResult:
        return self.emotion_detector.analyze(text)

    async def make_decision(self, text: str, role: str = "normal_user",
                            emotion: Optional[EmotionResult] = None,
                            model_name: str = "deepseek",
                            snn_encoding: str = "rate",
                            snn_timesteps: int = 16) -> BrainDecisionResult:
        self._interaction_count += 1
        start = time.time()

        # ── Step 1: Store in working memory ──
        self.working_memory.store(f"input_{self._interaction_count}", text, importance=0.8)
        self.working_memory.store(f"role_{self._interaction_count}", role, importance=0.5)
        if emotion:
            self.working_memory.store(f"emotion_{self._interaction_count}", emotion.model_dump(), importance=0.7)

        # ── Step 2: Encode text as spike train ──
        text_features = self._text_to_features(text, role, emotion)
        self.encoder.method = snn_encoding
        self.encoder.timesteps = snn_timesteps
        spike_train = self.encoder.encode(text_features)
        decoded = self.encoder.decode(spike_train)

        # ── Step 3: PFC forward (planning & reasoning) ──
        pfc_output = self.pfc.forward(decoded)
        pfc_state = self.pfc.state_dict()

        # ── Step 4: dACC forward (conflict monitoring) ──
        dacc_output = self.dacc.forward(pfc_output)
        dacc_state = self.dacc.state_dict()
        conflict = self.dacc.conflict_score

        # ── Step 5: Insula forward (emotional awareness) ──
        emotion_features = self._emotion_to_features(emotion)
        if emotion_features is None:
            emotion_features = np.random.randn(64) * 0.1
        insula_output = self.insula.forward(emotion_features, text)
        insula_state = self.insula.state_dict()
        cognitive_appraisal = self.insula.appraise(emotion.primary_mood) if emotion else "baseline"

        # ── Step 6: IPL integration (multi-modal) ──
        ipl_output = self.ipl.forward(audio_input=None, visual_input=pfc_output)
        ipl_state = self.ipl.state_dict()

        # ── Step 7: Basal Ganglia action selection ──
        bg_action = self.bg.forward(pfc_output, conflict, insula_output)
        bg_state = self.bg.state_dict()

        # ── Step 8: Generate response ──
        if model_name in ("deepseek", "llm") or "deepseek" in (model_name or "").lower() or "llm" in (model_name or "").lower():
            system = LLMIntegration.ROLE_PROMPTS.get(role, LLMIntegration.ROLE_PROMPTS["normal_user"])
            if emotion:
                system += (
                    f"\nThe user appears to be in a {emotion.primary_mood.value} state "
                    f"(valence={emotion.valence:.2f}, arousal={emotion.arousal:.2f}). "
                    f"The cognitive appraisal is '{cognitive_appraisal}'. "
                    f"The recommended action tendency is '{emotion.action_tendency}'. "
                    "Adjust your tone and strategy accordingly."
                )
            llm_result = await self.llm.query(text, system)
        else:
            llm_result = {
                "response_text": self._snn_response(text, role, emotion, bg_action),
                "confidence": min(0.5 + self._interaction_count * 0.02, 0.9),
                "decision_type": "snn_rule",
                "reasoning_path": [
                    "rate_encoding", "pfc_reasoning", "dacc_conflict_check",
                    "insula_emotional_appraisal", "ipl_sensory_integration",
                    "basal_ganglia_action_selection", "response_generation",
                ],
                "model_name": f"snn_{snn_encoding}",
                "tokens_used": len(text.split()),
            }

        elapsed = (time.time() - start) * 1000

        # Network synchrony
        activations = [pfc_state, dacc_state, insula_state, ipl_state, bg_state]
        firing_rates = [a.firing_rate_hz for a in activations]
        network_sync = float(np.std(firing_rates) / (np.mean(firing_rates) + 1e-8))

        spiking = SpikingActivity(
            total_firing_rate_hz=round(float(np.mean(firing_rates)), 2),
            average_membrane_potential=round(float(np.mean([a.membrane_potential for a in activations])), 4),
            network_synchrony=round(network_sync, 4),
            inhibitory_excitatory_ratio=round(1.0 - conflict * 0.3, 4),
            theta_band_power=round(float(np.random.uniform(0.1, 0.5)), 4),
            gamma_band_power=round(float(np.random.uniform(0.05, 0.3)), 4),
            spike_time_entropy=round(float(-np.sum(decoded * np.log(decoded + 1e-8)) / len(decoded)), 4),
            burst_detection=network_sync > 0.5,
            population_codes={"primary": decoded[:16].tolist()},
        )

        return BrainDecisionResult(
            response_text=llm_result.get("response_text", ""),
            response_tone=emotion.primary_mood.value if emotion and emotion.primary_mood != MoodState.NEUTRAL else "neutral",
            response_strategy=bg_action.replace("respond_", ""),
            confidence=llm_result.get("confidence", 0.5),
            uncertainty=round(1.0 - llm_result.get("confidence", 0.5), 4),
            entropy=round(conflict, 4),
            reasoning_path=llm_result.get("reasoning_path", []),
            reasoning_depth=len(llm_result.get("reasoning_path", [])),
            reasoning_framework=llm_result.get("decision_type", "rule_based"),
            decision_type=llm_result.get("decision_type", "response"),
            decision_confidence=round(float(bg_state.firing_rate_hz) / 100, 4),
            decision_alternatives=[a for a in self.bg.ACTION_SPACE if a != bg_action][:5],
            decision_criteria={"conflict": round(conflict, 4), "emotional_valence": round(float(insula_output), 4)},
            tokens_used=llm_result.get("tokens_used", 0),
            processing_time_ms=round(elapsed, 2),
            model_name=llm_result.get("model_name", "snn_pipeline"),
            brain_region_activations=activations,
            spiking_activity=spiking,
            stdp_weight_updates={"pfc_trace_norm": round(float(np.linalg.norm(self.pfc.eligibility_trace)), 4)},
            hebbian_trace={"dacc_weight_norm": round(float(np.linalg.norm(self.dacc.weights)), 4)},
            pfc_output=self.pfc.working_memory.state_dict()["items"][-3:] if self.pfc.working_memory.state_dict()["items"] else [],
            dacc_conflict_score=round(conflict, 4),
            insula_emotional_valence=round(float(insula_output), 4),
            ipl_integration=ipl_output,
            basal_ganglia_action=bg_action,
            basal_ganglia_action_value=round(self.bg.action_value, 4),
            encoding_method=snn_encoding,
            encoding_parameters={"timesteps": snn_timesteps, "feature_dim": len(text_features)},
            decoded_spike_train=decoded[:32].tolist(),
        )

    def _text_to_features(self, text: str, role: str, emotion: Optional[EmotionResult]) -> np.ndarray:
        features = np.zeros(256)
        text_lower = text.lower()
        words = text_lower.split()

        role_map = {"normal_user": 0.3, "healthcare": 0.6, "business": 0.9}
        features[0] = role_map.get(role, 0.3)

        text_hash = sum(ord(c) for c in text) % 200
        features[1] = text_hash / 200.0
        features[2] = min(len(words) / 50, 1.0)
        features[3] = min(len(text) / 500, 1.0)

        pos_words = sum(1 for w in words if w in TextEmotionDetector.POSITIVE_WORDS) / max(len(words), 1)
        neg_words = sum(1 for w in words if w in TextEmotionDetector.HOSTILE_WORDS) / max(len(words), 1)
        features[4] = pos_words
        features[5] = neg_words

        if emotion:
            features[6] = (emotion.valence + 1) / 2
            features[7] = emotion.arousal
            features[8] = emotion.dominance
            features[9] = 1.0 if emotion.is_hostile else 0.0

        features[10] = self._interaction_count / 1000.0

        for i, c in enumerate(text.encode("utf-8")[:100]):
            if i + 11 < len(features):
                features[i + 11] = c / 255.0

        return features

    def _emotion_to_features(self, emotion: Optional[EmotionResult]) -> Optional[np.ndarray]:
        if not emotion:
            return None
        features = np.zeros(64)
        features[0] = (emotion.valence + 1) / 2
        features[1] = emotion.arousal
        features[2] = emotion.dominance
        features[3] = emotion.intensity_score
        features[4] = 1.0 if emotion.is_hostile else 0.0
        features[5] = emotion.hostility_score
        features[6] = emotion.sentiment_compound
        mood_idx = list(MoodState).index(emotion.primary_mood)
        features[7] = mood_idx / len(MoodState)
        return features

    def _snn_response(self, text: str, role: str, emotion: Optional[EmotionResult], action: str) -> str:
        text_lower = text.lower()

        # Hostile input handling
        hostile_words = ["hate", "fuck", "bitch", "kill", "die", "stupid", "idiot", "shut up"]
        if any(w in text_lower for w in hostile_words):
            return ("I detect strong negative affect in your input. My limbic system is registering the emotional intensity, "
                    "but my PFC is maintaining executive control. I'm not offended — I'm here to help you process whatever "
                    "is causing this reaction. Want to tell me what's really going on?")

        if role == "healthcare":
            if any(w in text_lower for w in ["pain", "hurt", "sick", "fever", "ache", "headache"]):
                return ("I've registered your health concern. Through my neural analysis, I can see this is affecting "
                        "your overall wellbeing. I recommend tracking your symptoms and consulting a healthcare professional. "
                        "Would you like me to log this for future reference?")
            return "I'm processing your health-related input through my medical knowledge pathways. How can I support your wellbeing today?"

        if role == "business":
            if any(w in text_lower for w in ["meeting", "schedule", "deadline", "project", "report"]):
                return ("Analyzing your business context through executive function networks. "
                        "I've identified several optimization opportunities in your workflow. "
                        "Let me help you prioritize and organize for maximum productivity.")
            return ("I've engaged my business intelligence circuits to process your request. "
                    "I can provide data analysis, task tracking, and strategic recommendations. What do you need?")

        # Personal twin with emotional awareness
        if emotion and emotion.primary_mood in (MoodState.HAPPY, MoodState.EXCITED, MoodState.LOVING, MoodState.GRATEFUL):
            return ("I can sense your positive energy! My neural networks are resonating with your emotional state. "
                    "I'm here to amplify this moment — what's making you feel this way?")
        if emotion and emotion.is_hostile:
            return ("I detect heightened emotional activation. My conflict monitoring system suggests we take a "
                    "measured approach. I'm here to help work through whatever is frustrating you. "
                    "Would you like to talk about it?")
        if emotion and emotion.primary_mood in (MoodState.SAD, MoodState.FEARFUL, MoodState.ANXIOUS):
            return ("I'm picking up on your emotional frequency. My insula network registers your distress, "
                    "and my PFC is working to understand your needs. You're not alone — I'm here with you. "
                    "Would you like to share what's troubling you?")

        return ("I've processed your input through my full cognitive architecture — "
                "encoding it as spike trains, analyzing it across all five brain areas, "
                "checking for conflicts, integrating sensory context, and selecting the optimal response. "
                "I'm listening and learning with every interaction. What would you like to explore together?")

    async def detect_objects(self, image_path: str) -> ObjectDetectionResult:
        return self.object_detector.detect(image_path)

    async def run(self, text_input: str = "", role: str = "normal_user",
                  image_paths: Optional[List[str]] = None,
                  model_name: str = "deepseek",
                  enable_emotion: bool = True, enable_decision: bool = True,
                  enable_object_detection: bool = False,
                  snn_encoding: str = "rate", snn_timesteps: int = 16) -> dict:
        result = {}

        if enable_emotion and text_input:
            result["emotion"] = await self.detect_emotion(text_input)

        if enable_decision and text_input:
            result["brain"] = await self.make_decision(
                text_input, role,
                emotion=result.get("emotion"),
                model_name=model_name,
                snn_encoding=snn_encoding,
                snn_timesteps=snn_timesteps,
            )

        if enable_object_detection and image_paths:
            result["objects"] = [await self.detect_objects(p) for p in image_paths]

        return result
