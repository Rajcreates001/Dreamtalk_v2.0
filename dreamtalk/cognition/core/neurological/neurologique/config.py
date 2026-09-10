# Dreamtalk - Cognition Module
# Extracted from NeurologiqueTWIN (https://github.com/anomalyco/NeurologiqueTWIN)
# License: MIT

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


# ---------------------------------------------------------------------------
# Brain region definitions (10-20 international EEG system)
# ---------------------------------------------------------------------------

@dataclass
class BrainRegionDef:
    name: str
    lobe: str
    side: str
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    color_normal: str = "#3b82f6"
    color_alert: str = "#ef4444"
    function: str = ""
    is_active: bool = False
    activation: float = 0.0

    def activate(self, intensity: float = 1.0) -> None:
        self.is_active = True
        self.activation = max(0.0, min(1.0, intensity))

    def deactivate(self) -> None:
        self.is_active = False
        self.activation = 0.0

    def current_color(self) -> str:
        if not self.is_active or self.activation == 0.0:
            return self.color_normal
        if self.activation >= 0.8:
            return self.color_alert
        return "#f97316"

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "lobe": self.lobe,
            "side": self.side,
            "x": self.x, "y": self.y, "z": self.z,
            "color_normal": self.color_normal,
            "color_alert": self.color_alert,
            "color_current": self.current_color(),
            "function": self.function,
            "is_active": self.is_active,
            "activation": round(self.activation, 3),
        }


LOBE_COLORS = {
    "frontal": ("#3b82f6", "#ef4444"),
    "temporal": ("#8b5cf6", "#f97316"),
    "parietal": ("#10b981", "#eab308"),
    "occipital": ("#06b6d4", "#ec4899"),
    "central": ("#f59e0b", "#dc2626"),
}

LOBE_FUNCTIONS = {
    "frontal": "Motor control, planning, executive function, decision-making",
    "temporal": "Auditory processing, memory consolidation (hippocampus), language (Wernicke's area)",
    "parietal": "Sensory integration, spatial awareness, attention",
    "occipital": "Visual processing, pattern recognition",
    "central": "Primary motor cortex (M1) and primary somatosensory cortex (S1)",
}

def _make_regions() -> dict[str, BrainRegionDef]:
    fc, fa = LOBE_COLORS["frontal"]
    tc, ta = LOBE_COLORS["temporal"]
    pc, pa = LOBE_COLORS["central"]
    pac, paa = LOBE_COLORS["parietal"]
    oc, oa = LOBE_COLORS["occipital"]
    return {
        "Left Prefrontal": BrainRegionDef(
            name="Left Prefrontal", lobe="frontal", side="left",
            x=-0.30, y=0.85, z=0.20,
            color_normal=fc, color_alert=fa,
            function="Executive function, working memory, personality",
        ),
        "Right Prefrontal": BrainRegionDef(
            name="Right Prefrontal", lobe="frontal", side="right",
            x=0.30, y=0.85, z=0.20,
            color_normal=fc, color_alert=fa,
            function="Executive function, working memory, personality",
        ),
        "Left Frontal": BrainRegionDef(
            name="Left Frontal", lobe="frontal", side="left",
            x=-0.50, y=0.60, z=0.50,
            color_normal=fc, color_alert=fa,
            function="Voluntary movement (Broca's area), speech production",
        ),
        "Right Frontal": BrainRegionDef(
            name="Right Frontal", lobe="frontal", side="right",
            x=0.50, y=0.60, z=0.50,
            color_normal=fc, color_alert=fa,
            function="Voluntary movement, non-verbal communication",
        ),
        "Left Frontotemporal": BrainRegionDef(
            name="Left Frontotemporal", lobe="frontal", side="left",
            x=-0.80, y=0.40, z=0.15,
            color_normal=fc, color_alert=fa,
            function="Language, frontal-temporal integration",
        ),
        "Right Frontotemporal": BrainRegionDef(
            name="Right Frontotemporal", lobe="frontal", side="right",
            x=0.80, y=0.40, z=0.15,
            color_normal=fc, color_alert=fa,
            function="Prosody, emotional tone of language",
        ),
        "Frontal Midline": BrainRegionDef(
            name="Frontal Midline", lobe="frontal", side="midline",
            x=0.00, y=0.65, z=0.65,
            color_normal=fc, color_alert=fa,
            function="Supplementary motor area, anterior cingulate",
        ),
        "Left Temporal": BrainRegionDef(
            name="Left Temporal", lobe="temporal", side="left",
            x=-1.00, y=-0.05, z=0.10,
            color_normal=tc, color_alert=ta,
            function="Wernicke's area, verbal memory, auditory processing",
        ),
        "Right Temporal": BrainRegionDef(
            name="Right Temporal", lobe="temporal", side="right",
            x=1.00, y=-0.05, z=0.10,
            color_normal=tc, color_alert=ta,
            function="Non-verbal memory, music processing, face recognition",
        ),
        "Left Post-Temporal": BrainRegionDef(
            name="Left Post-Temporal", lobe="temporal", side="left",
            x=-0.85, y=-0.45, z=0.20,
            color_normal=tc, color_alert=ta,
            function="Visual-verbal integration, reading",
        ),
        "Right Post-Temporal": BrainRegionDef(
            name="Right Post-Temporal", lobe="temporal", side="right",
            x=0.85, y=-0.45, z=0.20,
            color_normal=tc, color_alert=ta,
            function="Spatial memory, navigation",
        ),
        "Left Motor Cortex": BrainRegionDef(
            name="Left Motor Cortex", lobe="central", side="left",
            x=-0.70, y=0.00, z=0.80,
            color_normal=pc, color_alert=pa,
            function="Primary motor cortex — controls right body movement",
        ),
        "Right Motor Cortex": BrainRegionDef(
            name="Right Motor Cortex", lobe="central", side="right",
            x=0.70, y=0.00, z=0.80,
            color_normal=pc, color_alert=pa,
            function="Primary motor cortex — controls left body movement",
        ),
        "Vertex (Motor)": BrainRegionDef(
            name="Vertex (Motor)", lobe="central", side="midline",
            x=0.00, y=0.00, z=1.00,
            color_normal=pc, color_alert=pa,
            function="Supplementary motor area, bilateral motor coordination",
        ),
        "Left Parietal": BrainRegionDef(
            name="Left Parietal", lobe="parietal", side="left",
            x=-0.55, y=-0.55, z=0.65,
            color_normal=pac, color_alert=paa,
            function="Sensory integration, number processing, language",
        ),
        "Right Parietal": BrainRegionDef(
            name="Right Parietal", lobe="parietal", side="right",
            x=0.55, y=-0.55, z=0.65,
            color_normal=pac, color_alert=paa,
            function="Spatial awareness, attention, visuospatial processing",
        ),
        "Parietal Midline": BrainRegionDef(
            name="Parietal Midline", lobe="parietal", side="midline",
            x=0.00, y=-0.50, z=0.85,
            color_normal=pac, color_alert=paa,
            function="Bilateral sensory integration, default mode network node",
        ),
        "Left Occipital": BrainRegionDef(
            name="Left Occipital", lobe="occipital", side="left",
            x=-0.35, y=-0.95, z=0.25,
            color_normal=oc, color_alert=oa,
            function="Right visual field processing",
        ),
        "Right Occipital": BrainRegionDef(
            name="Right Occipital", lobe="occipital", side="right",
            x=0.35, y=-0.95, z=0.25,
            color_normal=oc, color_alert=oa,
            function="Left visual field processing",
        ),
        "Occipital Midline": BrainRegionDef(
            name="Occipital Midline", lobe="occipital", side="midline",
            x=0.00, y=-1.00, z=0.15,
            color_normal=oc, color_alert=oa,
            function="Primary visual cortex (V1), bilateral visual integration",
        ),
    }

BRAIN_REGIONS: dict[str, BrainRegionDef] = _make_regions()

SEIZURE_TYPE_DEFAULT_REGION: dict[str, str | None] = {
    "Normal": None,
    "Absence": "Frontal Midline",
    "Focal Temporal": "Left Temporal",
    "Focal Frontal": "Left Frontal",
    "Myoclonic": "Vertex (Motor)",
    "Tonic": "Left Motor Cortex",
    "Tonic-Clonic": "Frontal Midline",
}


# ---------------------------------------------------------------------------
# Physiological feature specs for risk scoring
# ---------------------------------------------------------------------------

FEATURE_SPECS: dict[str, dict] = {
    "eeg_energy": {
        "baseline": 0.08, "std": 0.06, "weight": 0.30,
        "normal_range": (0.0, 0.25), "unit": "norm.",
        "label": "EEG Spectral Energy", "inverted": False,
    },
    "hr": {
        "baseline": 72.0, "std": 12.0, "weight": 0.22,
        "normal_range": (55.0, 90.0), "unit": "bpm",
        "label": "Heart Rate", "inverted": False,
    },
    "eda": {
        "baseline": 0.35, "std": 0.10, "weight": 0.18,
        "normal_range": (0.15, 0.60), "unit": "µS",
        "label": "Skin Conductance (EDA)", "inverted": False,
    },
    "hrv": {
        "baseline": 50.0, "std": 15.0, "weight": 0.15,
        "normal_range": (20.0, 80.0), "unit": "ms",
        "label": "Heart Rate Variability", "inverted": True,
    },
    "steps": {
        "baseline": 250.0, "std": 100.0, "weight": 0.07,
        "normal_range": (0.0, 600.0), "unit": "steps/h",
        "label": "Physical Activity", "inverted": True,
    },
    "stress": {
        "baseline": 0.25, "std": 0.15, "weight": 0.05,
        "normal_range": (0.0, 0.60), "unit": "score",
        "label": "Composite Stress Index", "inverted": False,
    },
    "tremor": {
        "baseline": 0.05, "std": 0.05, "weight": 0.03,
        "normal_range": (0.0, 0.20), "unit": "norm.",
        "label": "Tremor Index", "inverted": False,
    },
}

TABULAR_FEATURE_NAMES: list[str] = [
    "eeg_delta", "eeg_theta", "eeg_alpha", "eeg_beta", "eeg_gamma",
    "eeg_spectral_entropy", "eeg_hjorth_mobility", "eeg_hjorth_complexity",
    "eeg_mean", "eeg_std", "eeg_skewness", "eeg_kurtosis",
    "eeg_line_length", "eeg_zero_crossing_rate",
    "hr_deviation", "hrv_rmssd", "eda_level",
    "steps_per_hour", "stress_index", "tremor_index",
]

# Digital twin Markov state definitions
STATES = ["normal", "preictal", "ictal", "postictal"]

BASE_TRANSITION = [
    [0.94, 0.06, 0.00, 0.00],
    [0.08, 0.62, 0.30, 0.00],
    [0.00, 0.05, 0.55, 0.40],
    [0.20, 0.00, 0.00, 0.80],
]

RISK_BIAS = [
    [-0.5, +0.5, 0.00, 0.00],
    [-0.3, -0.2, +0.5, 0.00],
    [0.00, 0.00, +0.2, -0.2],
    [+0.3, 0.00, 0.00, -0.3],
]

STATE_RISK_MAP: dict[str, float] = {
    "normal": 0.05,
    "preictal": 0.55,
    "ictal": 0.92,
    "postictal": 0.30,
}

BRAIN_STATUS_THRESHOLDS: dict[str, float] = {
    "ictal": 0.80,
    "preictal": 0.60,
    "elevated": 0.40,
}

STATUS_LABELS: dict[str, str] = {
    "stable": "Stable — No significant seizure activity",
    "elevated": "Elevated Risk — Increased monitoring recommended",
    "preictal": "Pre-ictal — Possible seizure onset, notify caregiver",
    "ictal": "ICTAL — Active seizure suspected",
    "postictal": "Post-ictal — Recovery phase, patient may be confused",
}

STATUS_COLORS: dict[str, str] = {
    "stable": "#22c55e",
    "elevated": "#eab308",
    "preictal": "#f97316",
    "ictal": "#ef4444",
    "postictal": "#8b5cf6",
}

ALERT_LEVELS: dict[str, str] = {
    "stable": "info",
    "elevated": "yellow",
    "preictal": "orange",
    "ictal": "red",
    "postictal": "purple",
}


# ---------------------------------------------------------------------------
# Configuration dataclass
# ---------------------------------------------------------------------------

@dataclass
class NeurologiqueConfig:
    fs: float = 256.0
    lowcut: float = 0.5
    highcut: float = 50.0
    notch_freq: float = 50.0
    epoch_len_s: float = 4.0
    overlap: float = 0.5

    fs_ppg: float = 64.0
    fs_acc: float = 50.0
    fs_eda: float = 4.0
    hr_baseline: float = 72.0
    eda_baseline: float = 0.35

    image_size: int = 64
    n_bins: int = 8

    risk_threshold: float = 0.75
    history_len: int = 60
    alert_cooldown_s: float = 30.0
    min_consecutive: int = 2
    ema_alpha: float = 0.30
    deterministic: bool = False

    trend_boost: float = 0.10
    trend_window: int = 10
    risk_ema_alpha: float = 0.35

    postictal_grace_s: float = 30.0
    max_history: int = 100

    fusion_weights: dict[str, float] = field(default_factory=lambda: {
        "cnn": 0.35, "xgboost": 0.30, "nlp": 0.15, "imu": 0.15, "state": 0.05,
    })

    def to_dict(self) -> dict[str, Any]:
        return {k: v for k, v in self.__dict__.items() if not k.startswith("_")}


DEFAULT_CONFIG = NeurologiqueConfig()
