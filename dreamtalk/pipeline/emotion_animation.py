"""
DreamTalk — Emotion to Animation Mapper

Converts brain emotion output (PAD model, valence/arousal/dominance) 
into avatar facial animation parameters (blendshapes, transforms).

Supports:
- PAD (Pleasure-Arousal-Dominance) → avatar blendshape mapping
- Emotion-modulated eyebrow, eye, mouth, head parameters
- Temporal smoothing for natural-looking transitions
- Multi-emotion blending
"""

import time
import logging
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass, field
import math

logger = logging.getLogger("dreamtalk.pipeline.emotion_animation")


@dataclass
class AvatarExpression:
    """Complete avatar facial expression parameters."""
    # Eyebrows
    brow_inner_up: float = 0.0      # 0-1: inner brow raise
    brow_outer_up: float = 0.0      # 0-1: outer brow raise
    brow_lower: float = 0.0         # 0-1: brow lower (anger/sadness)

    # Eyes
    eye_open_left: float = 0.5      # 0-1: left eye openness
    eye_open_right: float = 0.5     # 0-1: right eye openness
    eye_squint_left: float = 0.0    # 0-1: left eye squint
    eye_squint_right: float = 0.0   # 0-1: right eye squint
    eye_wide_left: float = 0.0      # 0-1: left eye wide (surprise)
    eye_wide_right: float = 0.0     # 0-1: right eye wide (surprise)

    # Mouth
    mouth_open: float = 0.0         # 0-1: jaw drop
    mouth_smile_left: float = 0.0   # 0-1: left smile
    mouth_smile_right: float = 0.0  # 0-1: right smile
    mouth_frown_left: float = 0.0   # 0-1: left frown
    mouth_frown_right: float = 0.0  # 0-1: right frown
    mouth_pucker: float = 0.0       # 0-1: lip pucker
    mouth_funnel: float = 0.0       # 0-1: lip funnel
    mouth_stretch_left: float = 0.0 # 0-1: left mouth stretch
    mouth_stretch_right: float = 0.0 # 0-1: right mouth stretch

    # Head
    head_yaw: float = 0.0           # -1 to 1: left/right rotation
    head_pitch: float = 0.0         # -1 to 1: up/down tilt
    head_roll: float = 0.0          # -1 to 1: left/right tilt
    head_tilt: float = 0.0          # -1 to 1: forward/back tilt

    # Cheeks
    cheek_squint_left: float = 0.0  # 0-1: left cheek raise
    cheek_squint_right: float = 0.0 # 0-1: right cheek raise

    # Nose
    nose_sneer_left: float = 0.0    # 0-1: left nose sneer
    nose_sneer_right: float = 0.0   # 0-1: right nose sneer

    # Jaw
    jaw_open: float = 0.0           # 0-1: jaw openness

    # Meta
    emotion_label: str = "neutral"
    intensity: float = 1.0
    blend_weight: float = 1.0

    def to_dict(self) -> Dict:
        return {
            "eyebrows": {
                "brow_inner_up": round(self.brow_inner_up, 3),
                "brow_outer_up": round(self.brow_outer_up, 3),
                "brow_lower": round(self.brow_lower, 3),
            },
            "eyes": {
                "eye_open_left": round(self.eye_open_left, 3),
                "eye_open_right": round(self.eye_open_right, 3),
                "eye_squint_left": round(self.eye_squint_left, 3),
                "eye_squint_right": round(self.eye_squint_right, 3),
                "eye_wide_left": round(self.eye_wide_left, 3),
                "eye_wide_right": round(self.eye_wide_right, 3),
            },
            "mouth": {
                "mouth_open": round(self.mouth_open, 3),
                "mouth_smile_left": round(self.mouth_smile_left, 3),
                "mouth_smile_right": round(self.mouth_smile_right, 3),
                "mouth_frown_left": round(self.mouth_frown_left, 3),
                "mouth_frown_right": round(self.mouth_frown_right, 3),
                "mouth_pucker": round(self.mouth_pucker, 3),
                "mouth_funnel": round(self.mouth_funnel, 3),
                "mouth_stretch_left": round(self.mouth_stretch_left, 3),
                "mouth_stretch_right": round(self.mouth_stretch_right, 3),
            },
            "head": {
                "head_yaw": round(self.head_yaw, 3),
                "head_pitch": round(self.head_pitch, 3),
                "head_roll": round(self.head_roll, 3),
                "head_tilt": round(self.head_tilt, 3),
            },
            "cheeks": {
                "cheek_squint_left": round(self.cheek_squint_left, 3),
                "cheek_squint_right": round(self.cheek_squint_right, 3),
            },
            "jaw_open": round(self.jaw_open, 3),
            "emotion": self.emotion_label,
            "intensity": round(self.intensity, 3),
        }


# ── Emotion → Expression Presets ──────────────────────────────────────

EXPRESSION_PRESETS = {
    "happy": AvatarExpression(
        brow_inner_up=0.1, brow_outer_up=0.2,
        eye_open_left=0.7, eye_open_right=0.7,
        eye_squint_left=0.3, eye_squint_right=0.3,
        mouth_smile_left=0.8, mouth_smile_right=0.8,
        cheek_squint_left=0.5, cheek_squint_right=0.5,
        head_pitch=0.05,
        emotion_label="happy", intensity=1.0,
    ),
    "sad": AvatarExpression(
        brow_inner_up=0.5, brow_lower=0.3,
        eye_open_left=0.4, eye_open_right=0.4,
        mouth_frown_left=0.6, mouth_frown_right=0.6,
        head_pitch=-0.1, head_roll=0.05,
        emotion_label="sad", intensity=1.0,
    ),
    "angry": AvatarExpression(
        brow_lower=0.8, brow_inner_up=0.2,
        eye_open_left=0.8, eye_open_right=0.8,
        eye_squint_left=0.4, eye_squint_right=0.4,
        mouth_frown_left=0.4, mouth_frown_right=0.4,
        mouth_stretch_left=0.3, mouth_stretch_right=0.3,
        jaw_open=0.1, head_pitch=-0.05,
        emotion_label="angry", intensity=1.0,
    ),
    "surprised": AvatarExpression(
        brow_inner_up=0.9, brow_outer_up=0.8,
        eye_wide_left=0.9, eye_wide_right=0.9,
        eye_open_left=1.0, eye_open_right=1.0,
        mouth_open=0.6, jaw_open=0.5,
        head_pitch=0.1,
        emotion_label="surprised", intensity=1.0,
    ),
    "fearful": AvatarExpression(
        brow_inner_up=0.7, brow_outer_up=0.5,
        eye_wide_left=0.8, eye_wide_right=0.8,
        eye_open_left=0.9, eye_open_right=0.9,
        mouth_open=0.3, mouth_stretch_left=0.4, mouth_stretch_right=0.4,
        head_pitch=-0.05,
        emotion_label="fearful", intensity=1.0,
    ),
    "disgusted": AvatarExpression(
        brow_lower=0.4,
        eye_squint_left=0.5, eye_squint_right=0.5,
        nose_sneer_left=0.6, nose_sneer_right=0.6,
        mouth_frown_left=0.5, mouth_frown_right=0.5,
        mouth_pucker=0.3,
        emotion_label="disgusted", intensity=1.0,
    ),
    "calm": AvatarExpression(
        eye_open_left=0.6, eye_open_right=0.6,
        mouth_smile_left=0.2, mouth_smile_right=0.2,
        head_pitch=0.02,
        emotion_label="calm", intensity=0.8,
    ),
    "neutral": AvatarExpression(
        eye_open_left=0.5, eye_open_right=0.5,
        mouth_smile_left=0.05, mouth_smile_right=0.05,
        emotion_label="neutral", intensity=0.5,
    ),
    "excited": AvatarExpression(
        brow_inner_up=0.3, brow_outer_up=0.4,
        eye_wide_left=0.5, eye_wide_right=0.5,
        eye_open_left=0.8, eye_open_right=0.8,
        mouth_smile_left=0.9, mouth_smile_right=0.9,
        mouth_open=0.2,
        cheek_squint_left=0.4, cheek_squint_right=0.4,
        head_pitch=0.08, head_roll=0.05,
        emotion_label="excited", intensity=1.2,
    ),
    "loving": AvatarExpression(
        brow_inner_up=0.2, brow_outer_up=0.1,
        eye_open_left=0.5, eye_open_right=0.5,
        eye_squint_left=0.4, eye_squint_right=0.4,
        mouth_smile_left=0.7, mouth_smile_right=0.7,
        cheek_squint_left=0.6, cheek_squint_right=0.6,
        head_tilt=0.1,
        emotion_label="loving", intensity=1.0,
    ),
    "frustrated": AvatarExpression(
        brow_lower=0.6, brow_inner_up=0.3,
        eye_squint_left=0.3, eye_squint_right=0.3,
        mouth_frown_left=0.4, mouth_frown_right=0.4,
        mouth_stretch_left=0.2, mouth_stretch_right=0.2,
        head_roll=-0.05,
        emotion_label="frustrated", intensity=1.0,
    ),
    "confused": AvatarExpression(
        brow_inner_up=0.4, brow_outer_up=0.1,
        eye_squint_left=0.2, eye_squint_right=0.0,
        mouth_pucker=0.2,
        head_roll=0.1, head_yaw=0.1,
        emotion_label="confused", intensity=0.8,
    ),
}


class EmotionAnimationMapper:
    """Maps brain emotion output to avatar facial animation parameters.

    Features:
    - PAD model → expression preset lookup
    - Continuous interpolation between expressions
    - Intensity modulation
    - Temporal smoothing
    - Multi-emotion blending
    """

    def __init__(self, smoothing_factor: float = 0.3):
        self.smoothing_factor = smoothing_factor
        self._previous_expression: Optional[AvatarExpression] = None
        self._expression_history: List[AvatarExpression] = []
        self._max_history = 10

    def map_emotion(
        self,
        primary_mood: str,
        valence: float = 0.0,
        arousal: float = 0.5,
        dominance: float = 0.5,
        intensity_score: float = 0.5,
        secondary_mood: Optional[str] = None,
        secondary_weight: float = 0.3,
    ) -> AvatarExpression:
        """Map emotion parameters to avatar expression.

        Args:
            primary_mood: Primary emotion label (happy, sad, angry, etc.)
            valence: -1 to 1 (negative to positive)
            arousal: 0 to 1 (calm to excited)
            dominance: 0 to 1 (submissive to dominant)
            intensity_score: 0 to 1 (emotion intensity)
            secondary_mood: Optional secondary emotion for blending
            secondary_weight: Weight for secondary emotion (0-1)
        """
        # Get base expression from preset
        import dataclasses as _dc
        base = _dc.replace(EXPRESSION_PRESETS.get(primary_mood, EXPRESSION_PRESETS["neutral"]))

        # Apply intensity modulation
        base.intensity = min(max(intensity_score, 0.1), 1.5)

        # Apply arousal modulation (more arousal = more pronounced expressions)
        arousal_mod = 0.7 + 0.6 * arousal  # 0.7 to 1.3
        base.mouth_open *= arousal_mod
        base.eye_wide_left *= arousal_mod
        base.eye_wide_right *= arousal_mod

        # Apply dominance modulation (low dominance = more submissive expressions)
        dominance_mod = 0.8 + 0.4 * dominance  # 0.8 to 1.2
        base.head_pitch *= dominance_mod

        # Apply valence modulation (negative = more intense negative expressions)
        if valence < 0:
            base.mouth_frown_left *= (1 + abs(valence) * 0.5)
            base.mouth_frown_right *= (1 + abs(valence) * 0.5)
        else:
            base.mouth_smile_left *= (1 + valence * 0.3)
            base.mouth_smile_right *= (1 + valence * 0.3)

        # Blend with secondary emotion if provided
        if secondary_mood and secondary_weight > 0:
            import dataclasses as _dc
            secondary = _dc.replace(EXPRESSION_PRESETS.get(secondary_mood, EXPRESSION_PRESETS["neutral"]))
            base = self._blend_expressions(base, secondary, secondary_weight)

        # Apply temporal smoothing
        if self._previous_expression:
            base = self._smooth_expression(base, self._previous_expression)

        self._previous_expression = base
        self._expression_history.append(base)
        if len(self._expression_history) > self._max_history:
            self._expression_history = self._expression_history[-self._max_history:]

        return base

    def map_from_emotion_result(self, emotion_result) -> AvatarExpression:
        """Map from a pipeline EmotionResult object."""
        try:
            return self.map_emotion(
                primary_mood=emotion_result.primary_mood.value,
                valence=emotion_result.valence,
                arousal=emotion_result.arousal,
                dominance=emotion_result.dominance,
                intensity_score=emotion_result.intensity_score,
                secondary_mood=emotion_result.secondary_mood.value if emotion_result.secondary_mood else None,
            )
        except Exception as e:
            logger.warning(f"EmotionResult mapping failed: {e}")
            return EXPRESSION_PRESETS["neutral"]

    def get_idle_expression(self, time_seconds: float = 0.0) -> AvatarExpression:
        """Generate a natural idle animation (subtle breathing, blinking)."""
        # Subtle breathing
        breath_cycle = math.sin(time_seconds * 1.5) * 0.02
        # Subtle head movement
        head_sway = math.sin(time_seconds * 0.3) * 0.02
        # Blink simulation (every ~3-4 seconds)
        blink = max(0, math.sin(time_seconds * 1.8) - 0.95) * 10

        return AvatarExpression(
            eye_open_left=max(0.1, 0.5 - blink),
            eye_open_right=max(0.1, 0.5 - blink),
            mouth_smile_left=0.05 + breath_cycle,
            mouth_smile_right=0.05 + breath_cycle,
            jaw_open=breath_cycle * 0.5,
            head_yaw=head_sway,
            head_pitch=math.sin(time_seconds * 0.5) * 0.01,
            emotion_label="idle",
            intensity=0.3,
        )

    def _blend_expressions(
        self, expr_a: AvatarExpression, expr_b: AvatarExpression, weight_b: float
    ) -> AvatarExpression:
        """Blend two expressions with a weight."""
        w_a = 1.0 - weight_b
        w_b = weight_b

        blended = AvatarExpression(
            brow_inner_up=expr_a.brow_inner_up * w_a + expr_b.brow_inner_up * w_b,
            brow_outer_up=expr_a.brow_outer_up * w_a + expr_b.brow_outer_up * w_b,
            brow_lower=expr_a.brow_lower * w_a + expr_b.brow_lower * w_b,
            eye_open_left=expr_a.eye_open_left * w_a + expr_b.eye_open_left * w_b,
            eye_open_right=expr_a.eye_open_right * w_a + expr_b.eye_open_right * w_b,
            eye_squint_left=expr_a.eye_squint_left * w_a + expr_b.eye_squint_left * w_b,
            eye_squint_right=expr_a.eye_squint_right * w_a + expr_b.eye_squint_right * w_b,
            eye_wide_left=expr_a.eye_wide_left * w_a + expr_b.eye_wide_left * w_b,
            eye_wide_right=expr_a.eye_wide_right * w_a + expr_b.eye_wide_right * w_b,
            mouth_open=expr_a.mouth_open * w_a + expr_b.mouth_open * w_b,
            mouth_smile_left=expr_a.mouth_smile_left * w_a + expr_b.mouth_smile_left * w_b,
            mouth_smile_right=expr_a.mouth_smile_right * w_a + expr_b.mouth_smile_right * w_b,
            mouth_frown_left=expr_a.mouth_frown_left * w_a + expr_b.mouth_frown_left * w_b,
            mouth_frown_right=expr_a.mouth_frown_right * w_a + expr_b.mouth_frown_right * w_b,
            mouth_pucker=expr_a.mouth_pucker * w_a + expr_b.mouth_pucker * w_b,
            mouth_funnel=expr_a.mouth_funnel * w_a + expr_b.mouth_funnel * w_b,
            mouth_stretch_left=expr_a.mouth_stretch_left * w_a + expr_b.mouth_stretch_left * w_b,
            mouth_stretch_right=expr_a.mouth_stretch_right * w_a + expr_b.mouth_stretch_right * w_b,
            head_yaw=expr_a.head_yaw * w_a + expr_b.head_yaw * w_b,
            head_pitch=expr_a.head_pitch * w_a + expr_b.head_pitch * w_b,
            head_roll=expr_a.head_roll * w_a + expr_b.head_roll * w_b,
            head_tilt=expr_a.head_tilt * w_a + expr_b.head_tilt * w_b,
            cheek_squint_left=expr_a.cheek_squint_left * w_a + expr_b.cheek_squint_left * w_b,
            cheek_squint_right=expr_a.cheek_squint_right * w_a + expr_b.cheek_squint_right * w_b,
            nose_sneer_left=expr_a.nose_sneer_left * w_a + expr_b.nose_sneer_left * w_b,
            nose_sneer_right=expr_a.nose_sneer_right * w_a + expr_b.nose_sneer_right * w_b,
            jaw_open=expr_a.jaw_open * w_a + expr_b.jaw_open * w_b,
            emotion_label=expr_a.emotion_label,
            intensity=expr_a.intensity * w_a + expr_b.intensity * w_b,
        )
        return blended

    def _smooth_expression(
        self, current: AvatarExpression, previous: AvatarExpression
    ) -> AvatarExpression:
        """Apply temporal smoothing between expressions."""
        s = self.smoothing_factor
        p = 1.0 - s

        return AvatarExpression(
            brow_inner_up=current.brow_inner_up * s + previous.brow_inner_up * p,
            brow_outer_up=current.brow_outer_up * s + previous.brow_outer_up * p,
            brow_lower=current.brow_lower * s + previous.brow_lower * p,
            eye_open_left=current.eye_open_left * s + previous.eye_open_left * p,
            eye_open_right=current.eye_open_right * s + previous.eye_open_right * p,
            eye_squint_left=current.eye_squint_left * s + previous.eye_squint_left * p,
            eye_squint_right=current.eye_squint_right * s + previous.eye_squint_right * p,
            eye_wide_left=current.eye_wide_left * s + previous.eye_wide_left * p,
            eye_wide_right=current.eye_wide_right * s + previous.eye_wide_right * p,
            mouth_open=current.mouth_open * s + previous.mouth_open * p,
            mouth_smile_left=current.mouth_smile_left * s + previous.mouth_smile_left * p,
            mouth_smile_right=current.mouth_smile_right * s + previous.mouth_smile_right * p,
            mouth_frown_left=current.mouth_frown_left * s + previous.mouth_frown_left * p,
            mouth_frown_right=current.mouth_frown_right * s + previous.mouth_frown_right * p,
            mouth_pucker=current.mouth_pucker * s + previous.mouth_pucker * p,
            mouth_funnel=current.mouth_funnel * s + previous.mouth_funnel * p,
            mouth_stretch_left=current.mouth_stretch_left * s + previous.mouth_stretch_left * p,
            mouth_stretch_right=current.mouth_stretch_right * s + previous.mouth_stretch_right * p,
            head_yaw=current.head_yaw * s + previous.head_yaw * p,
            head_pitch=current.head_pitch * s + previous.head_pitch * p,
            head_roll=current.head_roll * s + previous.head_roll * p,
            head_tilt=current.head_tilt * s + previous.head_tilt * p,
            cheek_squint_left=current.cheek_squint_left * s + previous.cheek_squint_left * p,
            cheek_squint_right=current.cheek_squint_right * s + previous.cheek_squint_right * p,
            nose_sneer_left=current.nose_sneer_left * s + previous.nose_sneer_left * p,
            nose_sneer_right=current.nose_sneer_right * s + previous.nose_sneer_right * p,
            jaw_open=current.jaw_open * s + previous.jaw_open * p,
            emotion_label=current.emotion_label,
            intensity=current.intensity * s + previous.intensity * p,
        )


# ── Singleton ──────────────────────────────────────────────────────────

_default_mapper: Optional[EmotionAnimationMapper] = None


def get_emotion_animation_mapper() -> EmotionAnimationMapper:
    """Get or create the default emotion animation mapper singleton."""
    global _default_mapper
    if _default_mapper is None:
        _default_mapper = EmotionAnimationMapper()
    return _default_mapper
