# Dreamtalk - Emotion Engine
# Migrated from Dreamtalk_Emotion_Engine

"""
Human-Like Emotion Engine for DreamTalk v3.5.
Implements PAD (Pleasure, Arousal, Dominance) with 50+ states and emotional inertia.
"""

import numpy as np
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional
import logging


@dataclass
class EmotionState:
    name: str
    p: float    # Pleasure (Valence: -1 to 1)
    a: float    # Arousal (Intensity: -1 to 1)
    d: float    # Dominance (Control: -1 to 1)


class PADEmotionEngine:
    def __init__(self, inertia: float = 0.85):
        self.inertia = inertia  # Higher = more stable mood (Emotional Inertia)
        self.current_pad = np.array([0.0, 0.0, 0.0])  # Start at Neutral

        # Expanded 50+ Emotional States in PAD space
        self.emotion_map = {
            # --- Positive & Active ---
            "ecstasy": EmotionState("Ecstasy", 0.9, 0.9, 0.8),
            "joy": EmotionState("Joy", 0.8, 0.5, 0.4),
            "excited": EmotionState("Excited", 0.7, 0.8, 0.5),
            "elated": EmotionState("Elated", 0.8, 0.7, 0.6),
            "triumphant": EmotionState("Triumphant", 0.7, 0.6, 0.9),
            "love": EmotionState("Love", 0.9, 0.4, 0.3),
            "lust": EmotionState("Lust", 0.6, 0.9, 0.5),
            "affection": EmotionState("Affection", 0.8, 0.2, 0.1),
            "playful": EmotionState("Playful", 0.6, 0.5, 0.2),
            "amazed": EmotionState("Amazed", 0.7, 0.9, 0.2),

            # --- Positive & Passive ---
            "calm": EmotionState("Calm", 0.4, -0.6, 0.1),
            "relaxed": EmotionState("Relaxed", 0.5, -0.5, 0.2),
            "serene": EmotionState("Serene", 0.6, -0.7, 0.3),
            "content": EmotionState("Content", 0.6, -0.3, 0.2),
            "satisfied": EmotionState("Satisfied", 0.7, -0.2, 0.4),
            "peaceful": EmotionState("Peaceful", 0.5, -0.8, 0.2),

            # --- Neutral/Curious ---
            "neutral": EmotionState("Neutral", 0.0, 0.0, 0.0),
            "curious": EmotionState("Curious", 0.3, 0.4, 0.2),
            "interested": EmotionState("Interested", 0.5, 0.3, 0.3),
            "surprised": EmotionState("Surprised", 0.2, 0.8, 0.0),
            "pensive": EmotionState("Pensive", 0.1, -0.2, -0.1),

            # --- Negative & Active (Aggressive) ---
            "rage": EmotionState("Rage", -0.9, 1.0, 0.8),
            "furious": EmotionState("Furious", -0.8, 0.9, 0.7),
            "angry": EmotionState("Angry", -0.7, 0.7, 0.6),
            "hostile": EmotionState("Hostile", -0.6, 0.6, 0.5),
            "irritated": EmotionState("Irritated", -0.4, 0.5, 0.3),
            "annoyed": EmotionState("Annoyed", -0.3, 0.4, 0.2),
            "jealous": EmotionState("Jealous", -0.5, 0.6, -0.2),
            "envious": EmotionState("Envious", -0.4, 0.5, -0.3),
            "sarcastic": EmotionState("Sarcastic", -0.2, 0.4, 0.5),

            # --- Negative & Active (Anxious) ---
            "panicked": EmotionState("Panicked", -0.8, 1.0, -0.9),
            "fearful": EmotionState("Fearful", -0.7, 0.9, -0.8),
            "anxious": EmotionState("Anxious", -0.5, 0.7, -0.6),
            "worried": EmotionState("Worried", -0.4, 0.5, -0.5),
            "apprehensive": EmotionState("Apprehensive", -0.3, 0.4, -0.4),
            "guilty": EmotionState("Guilty", -0.5, 0.4, -0.7),
            "ashamed": EmotionState("Ashamed", -0.6, 0.3, -0.8),

            # --- Negative & Passive ---
            "grief": EmotionState("Grief", -0.9, -0.2, -0.7),
            "depressed": EmotionState("Depressed", -0.8, -0.5, -0.8),
            "sad": EmotionState("Sad", -0.6, -0.3, -0.6),
            "disappointed": EmotionState("Disappointed", -0.5, -0.1, -0.4),
            "lonely": EmotionState("Lonely", -0.7, -0.4, -0.7),
            "bored": EmotionState("Bored", -0.2, -0.7, -0.3),
            "tired": EmotionState("Tired", -0.1, -0.8, -0.4),
            "apathetic": EmotionState("Apathetic", -0.3, -0.9, -0.5),

            # --- Complex Social ---
            "empathetic": EmotionState("Empathetic", 0.6, 0.3, 0.1),
            "compassionate": EmotionState("Compassionate", 0.7, 0.2, 0.2),
            "sympathetic": EmotionState("Sympathetic", 0.5, 0.2, 0.0),
            "defensive": EmotionState("Defensive", -0.3, 0.6, 0.4),
            "proud": EmotionState("Proud", 0.7, 0.5, 0.9),
            "contemptuous": EmotionState("Contemptuous", -0.5, 0.4, 0.7),
        }

    def update(self, stimulus_pad: Tuple[float, float, float]) -> Dict:
        """Update current PAD state with stimulus using emotional inertia."""
        stimulus = np.array(stimulus_pad)
        self.current_pad = (self.inertia * self.current_pad) + ((1 - self.inertia) * stimulus)
        return self.get_current_emotion()

    def get_current_emotion(self) -> Dict:
        """Find the closest named emotion and blended secondary states."""
        p, a, d = self.current_pad

        distances = []
        for name, state in self.emotion_map.items():
            dist = np.linalg.norm(self.current_pad - np.array([state.p, state.a, state.d]))
            distances.append((name, dist))

        distances.sort(key=lambda x: x[1])
        primary_name = distances[0][0]
        secondary_name = distances[1][0]

        return {
            "name": primary_name,
            "display_name": self.emotion_map[primary_name].name,
            "secondary_emotion": self.emotion_map[secondary_name].name,
            "vad": self.current_pad.tolist(),
            "pad": self.current_pad.tolist(),
            "intensity": self._get_intensity_level(a)
        }

    def _get_intensity_level(self, arousal: float) -> str:
        if arousal > 0.7: return "extreme"
        if arousal > 0.4: return "high"
        if arousal > 0.0: return "medium"
        if arousal > -0.4: return "low"
        return "minimal"

    def stimulus_from_sentiment(self, sentiment: float, dominance: float = 0.0) -> Tuple[float, float, float]:
        """Convert raw sentiment/input into a PAD stimulus."""
        p = sentiment
        a = abs(sentiment) * 0.8
        d = dominance
        return (p, a, d)
