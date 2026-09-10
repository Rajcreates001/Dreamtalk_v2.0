# Dreamtalk - Cognition Module
# Extracted from NeurologiqueTWIN (https://github.com/anomalyco/NeurologiqueTWIN)
# License: MIT

"""
NeuroInferenceEngine — consolidated inference pipeline for NeurologiqueTWIN.

Orchestrates:
  1. Feature extraction (EEG, IMU, tabular, NLP)
  2. Seizure risk prediction (image-based CNN, tabular XGBoost, NLP)
  3. Explainable risk scoring with attribution
  4. Digital twin Markov state machine
  5. Multimodal fusion
  6. Brain region mapping (10-20 system)
  7. Alert generation
"""

from __future__ import annotations

import math
import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Callable, Deque, Dict, List, Optional, Tuple

import numpy as np

from dreamtalk.cognition.core.neurological.neurologique.config import (
    NeurologiqueConfig,
    FEATURE_SPECS,
    TABULAR_FEATURE_NAMES,
    BRAIN_REGIONS,
    SEIZURE_TYPE_DEFAULT_REGION,
    STATES,
    BASE_TRANSITION,
    RISK_BIAS,
    STATE_RISK_MAP,
    BRAIN_STATUS_THRESHOLDS,
    STATUS_LABELS,
    STATUS_COLORS,
    ALERT_LEVELS,
    BrainRegionDef,
)
from dreamtalk.cognition.core.neurological.neurologique.models.eeg_processor import (
    EEGProcessor,
    TimeSeriesTransformer,
    to_rgb,
)
from dreamtalk.cognition.core.neurological.neurologique.models.imu_processor import (
    IMUProcessor,
    WearableFeatures,
)
from dreamtalk.cognition.core.neurological.neurologique.models.nlp_analyzer import (
    ClinicalNLPAnalyzer,
)


# ==============================================================================
# Event Bus
# ==============================================================================

@dataclass
class Event:
    id: str
    t: float
    type: str
    payload: Dict[str, Any]


class EventBus:
    def __init__(self) -> None:
        self._events: List[Event] = []
        self._subscribers: Dict[str, List[Callable[[Event], None]]] = {}

    def publish(self, type_: str, payload: Dict[str, Any]) -> Event:
        ev = Event(id=str(uuid.uuid4()), t=time.time(), type=type_, payload=payload)
        self._events.append(ev)
        for cb in self._subscribers.get(type_, []):
            try:
                cb(ev)
            except Exception:
                pass
        return ev

    def subscribe(self, type_: str, callback: Callable[[Event], None]) -> None:
        self._subscribers.setdefault(type_, []).append(callback)

    def drain(self) -> List[Event]:
        events = self._events[:]
        self._events.clear()
        return events

    def peek(self) -> List[Event]:
        return list(self._events)

    def filter(self, type_: str) -> List[Event]:
        return [e for e in self._events if e.type == type_]


# ==============================================================================
# Explainable Risk Scorer
# ==============================================================================

@dataclass
class FeatureContribution:
    name: str
    key: str
    value: float
    z_score: float
    contribution: float
    direction: str
    normal_range: Tuple[float, float]
    unit: str
    weight: float


@dataclass
class RiskExplanation:
    seizure_risk: float
    raw_risk: float
    ema_risk: float
    risk_level: str
    features: List[FeatureContribution]
    dominant_driver: str
    attribution_dict: Dict[str, float]
    clinical_note: str
    raw_features: Dict[str, float] = field(default_factory=dict)


class ExplainableRiskScorer:
    def __init__(
        self,
        feature_specs: Optional[Dict] = None,
        ema_alpha: float = 0.35,
        trend_boost: float = 0.10,
        trend_window: int = 10,
    ) -> None:
        self.specs = {**FEATURE_SPECS, **(feature_specs or {})}
        self.ema_alpha = ema_alpha
        self.trend_boost = trend_boost
        self.trend_window = trend_window
        self._ema: float = 0.0
        self._score_history: List[float] = []

    def score(self, features: Dict[str, float]) -> float:
        return self.explain(features).seizure_risk

    def explain(self, features: Dict[str, float]) -> RiskExplanation:
        contribs: List[FeatureContribution] = []
        total_contrib = 0.0

        for key, spec in self.specs.items():
            if key not in features:
                continue
            val = float(features[key])
            baseline = spec["baseline"]
            std = spec["std"]
            weight = spec["weight"]
            inverted = spec.get("inverted", False)

            z = (val - baseline) / (std + 1e-8)
            if inverted:
                z = -z

            contrib = weight * float(np.tanh(z * 0.75))
            total_contrib += contrib

            direction = (
                "increases_risk" if contrib > 0.015
                else "decreases_risk" if contrib < -0.015
                else "neutral"
            )
            contribs.append(FeatureContribution(
                name=spec["label"], key=key, value=val,
                z_score=round(z, 3), contribution=round(contrib, 4),
                direction=direction, normal_range=spec["normal_range"],
                unit=spec["unit"], weight=weight,
            ))

        raw_risk = float(self._sigmoid(total_contrib / 0.5))
        self._ema = self.ema_alpha * raw_risk + (1.0 - self.ema_alpha) * self._ema
        ema_risk = self._ema

        self._score_history.append(ema_risk)
        if len(self._score_history) > self.trend_window:
            self._score_history.pop(0)
        trend = self._trend_slope()
        boost = self.trend_boost * max(0.0, trend / 0.01)
        final_risk = float(np.clip(ema_risk + boost, 0.0, 1.0))

        attribution = {c.key: c.contribution for c in contribs}
        dominant = max(contribs, key=lambda c: abs(c.contribution)).name if contribs else "Unknown"
        risk_level = self._risk_level(final_risk)
        note = self._clinical_note(
            risk_level, dominant,
            [c for c in contribs if c.direction == "increases_risk"],
        )

        return RiskExplanation(
            seizure_risk=final_risk, raw_risk=raw_risk, ema_risk=ema_risk,
            risk_level=risk_level, features=contribs,
            dominant_driver=dominant, attribution_dict=attribution,
            clinical_note=note, raw_features=dict(features),
        )

    def reset(self) -> None:
        self._ema = 0.0
        self._score_history.clear()

    @staticmethod
    def _sigmoid(x: float) -> float:
        if (x := float(x)) > -500:
            return 1.0 / (1.0 + math.exp(-x))
        return 0.0

    def _trend_slope(self) -> float:
        h = self._score_history
        if len(h) < 3:
            return 0.0
        xs = np.arange(len(h), dtype=float)
        ys = np.array(h)
        p = np.polyfit(xs, ys, 1)
        return float(p[0])

    @staticmethod
    def _risk_level(risk: float) -> str:
        if risk >= 0.80: return "critical"
        if risk >= 0.55: return "high"
        if risk >= 0.30: return "moderate"
        return "low"

    @staticmethod
    def _clinical_note(risk_level: str, dominant: str, increasing: List[FeatureContribution]) -> str:
        names = ", ".join(c.name for c in increasing) or "multiple signals"
        if risk_level == "critical":
            return f"CRITICAL seizure risk. Primary driver: {dominant}. Elevated biomarkers: {names}. Immediate clinical review recommended."
        if risk_level == "high":
            return f"High seizure risk. {dominant} is the dominant contributor. Monitor closely: {names}."
        if risk_level == "moderate":
            return f"Moderate risk. Watch for changes in {dominant}. Consider medication review if sustained."
        return "Low seizure risk. Patient within normal physiological parameters."


# ==============================================================================
# Digital Twin (Markov State Machine)
# ==============================================================================

_BASE_TRANSITION_NP = np.array(BASE_TRANSITION, dtype=np.float64)
_RISK_BIAS_NP = np.array(RISK_BIAS, dtype=np.float64)


def _softmax(x: np.ndarray) -> np.ndarray:
    e = np.exp(x - x.max())
    return e / e.sum()


def _compute_transition(from_state: int, risk: float) -> np.ndarray:
    base_row = _BASE_TRANSITION_NP[from_state]
    log_base = np.log(np.clip(base_row, 1e-9, 1.0))
    bias = _RISK_BIAS_NP[from_state]
    log_eff = log_base + float(risk) * bias
    return _softmax(log_eff)


class DigitalTwin:
    def __init__(
        self,
        predictor: Callable[[Dict[str, Any]], float],
        bus: Optional[EventBus] = None,
        risk_threshold: float = 0.75,
        history_len: int = 60,
        alert_cooldown_s: float = 30.0,
        min_consecutive: int = 2,
        ema_alpha: float = 0.30,
        deterministic: bool = False,
    ) -> None:
        self.predictor = predictor
        self.bus = bus or EventBus()
        self.risk_threshold = float(risk_threshold)
        self.history_len = history_len
        self.alert_cooldown_s = alert_cooldown_s
        self.min_consecutive = min_consecutive
        self.ema_alpha = ema_alpha
        self.deterministic = deterministic

        self._state_idx: int = 0
        self._history: Deque[Tuple[float, float]] = deque(maxlen=history_len)
        self._risk_ema: float = 0.0
        self._consecutive_high: int = 0
        self._last_alert_t: float = 0.0
        self.last_pred: Optional[Dict[str, Any]] = None

    def step(self, features: Dict[str, Any], location: Optional[Dict[str, float]] = None) -> Dict[str, Any]:
        raw_risk = float(self.predictor(features))

        self._risk_ema = self.ema_alpha * raw_risk + (1.0 - self.ema_alpha) * self._risk_ema
        smooth_risk = self._risk_ema

        probs = _compute_transition(self._state_idx, smooth_risk)
        if self.deterministic:
            next_idx = int(np.argmax(probs))
        else:
            next_idx = int(np.random.choice(len(STATES), p=probs))
        self._state_idx = next_idx
        state = STATES[self._state_idx]

        now = time.time()
        self._history.append((now, smooth_risk))
        trend = self._compute_trend()
        risk_trend_label = self._trend_label(trend)

        if smooth_risk >= self.risk_threshold:
            self._consecutive_high += 1
        else:
            self._consecutive_high = 0

        loc = location or {"lat": 33.238, "lon": -8.500}
        alert_fired = False

        if self._consecutive_high >= self.min_consecutive and (now - self._last_alert_t) >= self.alert_cooldown_s:
            self._last_alert_t = now
            alert_fired = True
            self.bus.publish("alert", {
                "raw_risk": raw_risk, "smooth_risk": smooth_risk,
                "state": state, "trend": trend,
                "location": loc, "maps_link": _maps_link(loc),
                "consecutive_high": self._consecutive_high,
            })

        result: Dict[str, Any] = {
            "seizure_risk": smooth_risk, "raw_risk": raw_risk,
            "smooth_risk": smooth_risk, "state": state,
            "state_distribution": {s: float(p) for s, p in zip(STATES, probs)},
            "trend": trend, "risk_trend_label": risk_trend_label,
            "alert_fired": alert_fired,
            "consecutive_high": self._consecutive_high,
            "maps_link": _maps_link(loc),
            "timestamp": now, "features": features,
        }
        self.last_pred = result

        self.bus.publish("inference", {
            "raw_risk": raw_risk, "smooth_risk": smooth_risk,
            "state": state, "trend": trend,
        })
        return result

    @property
    def state(self) -> str:
        return STATES[self._state_idx]

    @property
    def risk_ema(self) -> float:
        return self._risk_ema

    def get_history(self) -> List[Dict[str, float]]:
        return [{"t": t, "risk": r} for t, r in self._history]

    def get_state_distribution(self) -> Dict[str, float]:
        probs = _compute_transition(self._state_idx, self._risk_ema)
        return {s: float(p) for s, p in zip(STATES, probs)}

    def reset(self) -> None:
        self._state_idx = 0
        self._history.clear()
        self._risk_ema = 0.0
        self._consecutive_high = 0
        self._last_alert_t = 0.0
        self.last_pred = None

    def _compute_trend(self) -> float:
        if len(self._history) < 3:
            return 0.0
        ts = np.array([h[0] for h in self._history])
        vs = np.array([h[1] for h in self._history])
        t0 = ts[0]
        xs = ts - t0
        n = len(xs)
        sx = xs.sum()
        sy = vs.sum()
        sxx = (xs ** 2).sum()
        sxy = (xs * vs).sum()
        denom = n * sxx - sx * sx
        if abs(denom) < 1e-12:
            return 0.0
        return float((n * sxy - sx * sy) / denom)

    @staticmethod
    def _trend_label(slope: float) -> str:
        if slope > 0.005: return "rising"
        if slope < -0.005: return "falling"
        return "stable"


def _maps_link(loc: Dict[str, float]) -> str:
    return f"https://www.google.com/maps?q={loc.get('lat', 0)},{loc.get('lon', 0)}"


# ==============================================================================
# Seizure Predictors
# ==============================================================================

class _FeatureFallbackScorer:
    """Lightweight linear scorer when no model is available."""

    @staticmethod
    def score(features: Dict) -> float:
        hr  = float(features.get("hr",  70.0))
        eda = float(features.get("eda", 0.30))
        eeg = float(features.get("eeg_energy", 0.0))
        z = (max(0.0, (hr  - 75.0) / 30.0) * 0.4
             + max(0.0, (eda - 0.35) / 0.50) * 0.4
             + eeg * 0.2)
        return float(np.clip(z, 0.0, 1.0))


class EnsembleSeizurePredictor:
    """
    Ensemble predictor that falls back gracefully.

    In production, loads ResNet-CBAM models for GASF/MTF/RP encodings.
    This implementation provides the interface with feature-based fallback.
    """

    def __init__(self, model_paths: Optional[Dict[str, str]] = None) -> None:
        self._predictors: List[Callable[[Dict], float]] = []
        if model_paths:
            for name, path in model_paths.items():
                try:
                    p = self._load_keras_model(path)
                    self._predictors.append(p)
                except Exception:
                    pass

    def _load_keras_model(self, path: str) -> Callable[[Dict], float]:
        try:
            import tensorflow as tf  # noqa: F811
            model = tf.keras.models.load_model(path, compile=False)
            def predict(features: Dict) -> float:
                if "rgb" in features:
                    img = np.asarray(features["rgb"])
                    if img.ndim == 2:
                        img = np.repeat(img[..., None], 3, axis=-1)
                    p = model.predict(img[None, ...], verbose=0)[0]
                    return float(np.clip(p[1] / (p.sum() + 1e-8), 0.0, 1.0))
                return _FeatureFallbackScorer.score(features)
            return predict
        except ImportError:
            return lambda features: _FeatureFallbackScorer.score(features)

    def __call__(self, features: Dict) -> float:
        if self._predictors:
            scores = [p(features) for p in self._predictors]
            return float(np.mean(scores))
        return _FeatureFallbackScorer.score(features)


# ==============================================================================
# Tabular Feature Extractor & Predictor
# ==============================================================================

class EEGFeatureExtractor:
    def __init__(self, fs: float = 256.0) -> None:
        self.fs = fs

    def extract(self, eeg: Optional[np.ndarray] = None, imu: Optional[Dict[str, float]] = None) -> np.ndarray:
        feat = np.zeros(20, dtype=np.float32)

        if eeg is not None and len(eeg) >= 32:
            eeg = eeg.astype(np.float64)
            spectral = self._spectral_features(eeg)
            stat = self._statistical_features(eeg)
            feat[0:8] = spectral
            feat[8:14] = stat
        else:
            eeg_en = float((imu or {}).get("eeg_energy", 0.08))
            feat[4] = eeg_en

        if imu is not None:
            hr     = float(imu.get("hr",     72.0))
            hrv    = float(imu.get("hrv",    50.0))
            eda    = float(imu.get("eda",     0.35))
            steps  = float(imu.get("steps",  250.0))
            stress = float(imu.get("stress",  0.25))
            tremor = float(imu.get("tremor",  0.05))
            feat[14] = (hr - 72.0) / 15.0
            feat[15] = hrv / 50.0
            feat[16] = eda / 0.60
            feat[17] = steps / 300.0
            feat[18] = stress
            feat[19] = tremor

        return feat

    def _spectral_features(self, eeg: np.ndarray) -> np.ndarray:
        fft = np.fft.rfft(eeg)
        freqs = np.fft.rfftfreq(len(eeg), d=1.0 / self.fs)
        power = np.abs(fft) ** 2
        total = power.sum() + 1e-12

        def bp(lo, hi):
            return float(power[(freqs >= lo) & (freqs < hi)].sum() / total)

        delta = bp(0.5, 4.0)
        theta = bp(4.0, 8.0)
        alpha = bp(8.0, 13.0)
        beta  = bp(13.0, 30.0)
        gamma = bp(30.0, 50.0)

        p_norm = power / total
        p_norm = np.clip(p_norm, 1e-12, 1.0)
        sp_entropy = float(-np.sum(p_norm * np.log(p_norm)) / np.log(len(p_norm)))

        dx = np.diff(eeg)
        ddx = np.diff(dx)
        var_x   = np.var(eeg)  + 1e-12
        var_dx  = np.var(dx)   + 1e-12
        var_ddx = np.var(ddx)  + 1e-12
        hjorth_mob   = float(np.sqrt(var_dx / var_x))
        hjorth_cplx  = float(np.sqrt(var_ddx / var_dx) / hjorth_mob)

        return np.array([delta, theta, alpha, beta, gamma,
                         sp_entropy, hjorth_mob, hjorth_cplx], dtype=np.float32)

    def _statistical_features(self, x: np.ndarray) -> np.ndarray:
        mu = x.mean()
        sigma = x.std() + 1e-8
        sk = float(np.mean(((x - mu) / sigma) ** 3))
        ku = float(np.mean(((x - mu) / sigma) ** 4) - 3)
        ll  = float(np.sum(np.abs(np.diff(x))))
        zcr = float(np.sum(np.diff(np.sign(x)) != 0) / len(x))
        return np.array([mu, x.std(), sk, ku, ll / (len(x) * 2), zcr], dtype=np.float32)


class TabularSeizurePredictor:
    def __init__(self, fs: float = 256.0) -> None:
        self.extractor = EEGFeatureExtractor(fs=fs)
        self._lr_weights = self._train_synthetic()

    def _train_synthetic(self) -> np.ndarray:
        np.random.seed(42)
        N = 1200

        def gen(n, hr_mu, hr_sd, eeg_mu, eeg_sd, eda_mu, eda_sd, hrv_mu, hrv_sd, steps_mu, steps_sd):
            X = np.zeros((n, 20), dtype=np.float32)
            hr    = np.random.normal(hr_mu, hr_sd, n)
            eeg   = np.random.normal(eeg_mu, eeg_sd, n).clip(0, 1)
            eda   = np.random.normal(eda_mu, eda_sd, n).clip(0.05, 2.0)
            hrv   = np.random.normal(hrv_mu, hrv_sd, n).clip(5, 120)
            steps = np.random.normal(steps_mu, steps_sd, n).clip(0, 600)

            gamma_frac = eeg / (eeg + 0.5)
            X[:, 4]  = gamma_frac * eeg
            X[:, 3]  = (1 - gamma_frac) * eeg * 0.7
            X[:, 2]  = eeg * 0.15
            X[:, 1]  = eeg * 0.10
            X[:, 0]  = eeg * 0.05
            X[:, 5]  = 0.5 - 0.4 * (eeg - 0.08)
            X[:, 6]  = 0.1 + eeg * 0.5
            X[:, 7]  = 1.0 + eeg * 2.0
            X[:, 8]  = np.random.normal(0, 0.1, n)
            X[:, 9]  = 0.3 + eeg * 0.5
            X[:, 10] = np.random.normal(0, 0.5, n)
            X[:, 11] = 2.5 + 2.0 * (eeg > 0.3).astype(float)
            X[:, 12] = eeg * 0.7
            X[:, 13] = 0.1 + eeg * 0.4
            X[:, 14] = (hr - 72.0) / 15.0
            X[:, 15] = hrv / 50.0
            X[:, 16] = eda / 0.60
            X[:, 17] = steps / 300.0
            X[:, 18] = np.clip((hr - 72) / 30 + (eda - 0.35) / 0.4, 0, 1)
            X[:, 19] = np.random.exponential(0.03, n).clip(0, 1)
            return X.clip(-5, 5)

        X_normal   = gen(N, 72, 5, 0.08, 0.04, 0.32, 0.06, 55, 10, 280, 80)
        X_preictal = gen(N, 86, 5, 0.43, 0.08, 0.50, 0.07, 32, 8, 120, 60)
        X_ictal    = gen(N, 92, 6, 0.63, 0.06, 0.62, 0.08, 18, 5, 40, 30)

        X = np.vstack([X_normal, X_preictal, X_ictal]).astype(np.float32)
        y = np.array([0] * N + [1] * N + [1] * N, dtype=np.int32)
        idx = np.random.permutation(len(y))
        X, y = X[idx], y[idx]

        X_norm = (X - X.mean(0)) / (X.std(0) + 1e-8)
        w = np.zeros(X_norm.shape[1] + 1, dtype=np.float64)
        lr = 0.05
        for _ in range(500):
            Xb = np.column_stack([np.ones(len(X_norm)), X_norm])
            logit = Xb @ w
            p = 1 / (1 + np.exp(-np.clip(logit, -20, 20)))
            grad = Xb.T @ (p - y) / len(y)
            w -= lr * grad
        return w

    def predict(self, eeg: Optional[np.ndarray] = None, imu: Optional[Dict[str, float]] = None) -> float:
        feat = self.extractor.extract(eeg, imu)
        w = self._lr_weights
        x_norm = (feat - feat.mean()) / (feat.std() + 1e-8)
        xb = np.concatenate([[1.0], x_norm])
        logit = float(xb @ w)
        return float(1 / (1 + np.exp(-np.clip(logit, -20, 20))))

    def __call__(self, features: Dict) -> float:
        imu = features
        eeg = np.asarray(features["eeg_raw"]) if "eeg_raw" in features else None
        return self.predict(eeg=eeg, imu=imu)


# ==============================================================================
# Multimodal Fusion
# ==============================================================================

@dataclass
class FusionResult:
    final_risk: float
    risk_level: str
    modalities: List[Dict]
    attribution: Dict[str, float]
    agreement: float
    confidence: float
    dominant_modality: str
    clinical_summary: str


class MultimodalFusionEngine:
    def __init__(self, weights: Optional[Dict[str, float]] = None) -> None:
        default = {"cnn": 0.35, "xgboost": 0.30, "nlp": 0.15, "imu": 0.15, "state": 0.05}
        self.weights = {**default, **(weights or {})}
        total = sum(self.weights.values())
        self.weights = {k: v / total for k, v in self.weights.items()}

    def fuse(
        self,
        cnn_risk: Optional[float] = None,
        xgboost_risk: Optional[float] = None,
        nlp_risk: Optional[float] = None,
        imu_risk: Optional[float] = None,
        twin_state: Optional[str] = None,
    ) -> FusionResult:
        state_risk: Optional[float] = None
        if twin_state is not None:
            state_risk = STATE_RISK_MAP.get(twin_state.lower(), 0.1)

        inputs = {
            "cnn": cnn_risk, "xgboost": xgboost_risk,
            "nlp": nlp_risk, "imu": imu_risk, "state": state_risk,
        }
        available = {k: v for k, v in inputs.items() if v is not None}
        if not available:
            return self._empty_result()

        weight_sum = sum(self.weights[k] for k in available)
        eff_weights = {k: self.weights[k] / weight_sum for k in available}

        final_risk = float(sum(eff_weights[k] * float(v) for k, v in available.items()))
        final_risk = float(np.clip(final_risk, 0.0, 1.0))

        score_sum = sum(eff_weights[k] * float(v) for k, v in available.items())
        attribution = {
            k: round(eff_weights[k] * float(v) / (score_sum + 1e-8), 4)
            for k, v in available.items()
        }

        modalities = [
            {"name": k, "risk": float(v), "weight": self.weights[k],
             "available": True, "contribution": attribution[k]}
            for k, v in available.items()
        ]
        for k in set(inputs) - set(available):
            modalities.append({"name": k, "risk": 0.0, "weight": self.weights[k],
                               "available": False, "contribution": 0.0})

        risks = np.array(list(available.values()), dtype=float)
        agreement = float(1.0 - np.std(risks) / (np.mean(risks) + 1e-8))
        agreement = float(np.clip(agreement, 0.0, 1.0))

        coverage = len(available) / len(inputs)
        confidence = float(agreement * coverage)
        dominant = max(attribution, key=attribution.get)
        risk_level = self._risk_level(final_risk)

        avail_names = [m["name"] for m in modalities if m["available"]]
        agr_str = "high agreement" if agreement > 0.7 else "moderate agreement" if agreement > 0.4 else "low agreement"
        summary = (
            f"Multimodal fusion ({', '.join(avail_names)}): {risk_level} risk ({final_risk:.1%}). "
            f"Dominant signal: {dominant}. Inter-modality {agr_str} ({agreement:.0%})."
        )

        return FusionResult(
            final_risk=final_risk, risk_level=risk_level,
            modalities=modalities, attribution=attribution,
            agreement=round(agreement, 4), confidence=round(confidence, 4),
            dominant_modality=dominant, clinical_summary=summary,
        )

    @staticmethod
    def _risk_level(risk: float) -> str:
        if risk >= 0.80: return "critical"
        if risk >= 0.55: return "high"
        if risk >= 0.30: return "moderate"
        return "low"

    @staticmethod
    def _empty_result() -> FusionResult:
        return FusionResult(
            final_risk=0.0, risk_level="low", modalities=[], attribution={},
            agreement=0.0, confidence=0.0, dominant_modality="none",
            clinical_summary="No modality data available.",
        )


# ==============================================================================
# Region Mapper (10-20 EEG Channel System)
# ==============================================================================

REGION_DISCLAIMER = (
    "HYPOTHESIZED AFFECTED ZONE — Academic digital twin demo only. "
    "This is NOT validated clinical localization."
)


def compute_highlight_intensity(seizure_risk: float, threshold_min: float = 0.40) -> float:
    if seizure_risk < threshold_min:
        return 0.0
    return round(min(1.0, (seizure_risk - threshold_min) / (1.0 - threshold_min)), 4)


def risk_to_color(seizure_risk: float) -> str:
    if seizure_risk >= 0.80: return "#ef4444"
    if seizure_risk >= 0.60: return "#f97316"
    if seizure_risk >= 0.40: return "#eab308"
    return "#22c55e"


class RegionMapper:
    def resolve(
        self,
        seizure_risk: float = 0.0,
        seizure_type: Optional[str] = None,
        channel_scores: Optional[Dict[str, float]] = None,
        dominant_channels: Optional[List[str]] = None,
    ) -> dict:
        region: Optional[BrainRegionDef] = None
        confidence = "none"

        if channel_scores and any(abs(v) > 0 for v in channel_scores.values()):
            region, confidence = self._from_channel_scores(channel_scores)
            typical_chs = [ch for ch, v in sorted(channel_scores.items(), key=lambda x: -abs(x[1]))[:5]]
        elif dominant_channels:
            scores = {ch: 1.0 for ch in dominant_channels}
            region, confidence = self._from_channel_scores(scores)
            typical_chs = dominant_channels[:5]
        elif seizure_type:
            region_name = SEIZURE_TYPE_DEFAULT_REGION.get(seizure_type)
            region = BRAIN_REGIONS.get(region_name) if region_name else None
            confidence = "demo_seizure_type"
            typical_chs = []
        else:
            region = BRAIN_REGIONS.get("Frontal Midline")
            confidence = "fallback"
            typical_chs = ["Fz"]

        if region is None:
            region = BRAIN_REGIONS.get("Frontal Midline")
            confidence = "fallback"
            typical_chs = ["Fz"]

        intensity = compute_highlight_intensity(seizure_risk)
        color_hl  = risk_to_color(seizure_risk)

        return {
            "region_name": region.name,
            "lobe": region.lobe, "side": region.side,
            "x": region.x, "y": region.y, "z": region.z,
            "highlight_intensity": intensity,
            "localization_confidence": confidence,
            "color_normal": region.color_normal,
            "color_alert": region.color_alert,
            "color_highlight": color_hl,
            "function": region.function,
            "typical_channels": typical_chs,
            "disclaimer": REGION_DISCLAIMER,
        }

    def _from_channel_scores(self, channel_scores: Dict[str, float]) -> Tuple[Optional[BrainRegionDef], str]:
        CHANNEL_TO_REGION = {
            "FP1": "Left Prefrontal", "FP2": "Right Prefrontal",
            "F7": "Left Frontotemporal", "F8": "Right Frontotemporal",
            "F3": "Left Frontal", "F4": "Right Frontal", "FZ": "Frontal Midline",
            "T3": "Left Temporal", "T4": "Right Temporal",
            "T5": "Left Post-Temporal", "T6": "Right Post-Temporal",
            "C3": "Left Motor Cortex", "C4": "Right Motor Cortex", "CZ": "Vertex (Motor)",
            "P3": "Left Parietal", "P4": "Right Parietal", "PZ": "Parietal Midline",
            "O1": "Left Occipital", "O2": "Right Occipital", "OZ": "Occipital Midline",
        }

        region_votes: Dict[str, float] = {}
        for ch, score in channel_scores.items():
            ch_norm = ch.strip().upper().replace(" ", "").replace("-", "")
            region_name = CHANNEL_TO_REGION.get(ch_norm)
            if region_name and abs(score) > 0:
                region_votes[region_name] = region_votes.get(region_name, 0.0) + abs(float(score))

        if not region_votes:
            return None, "unknown"

        best = max(region_votes, key=lambda k: region_votes[k])
        return BRAIN_REGIONS.get(best), "channel_weighted"


# ==============================================================================
# Brain State & Alert Management
# ==============================================================================

class BrainTwinState:
    def __init__(self, patient_id: str, max_history: int = 100, postictal_grace_s: float = 30.0) -> None:
        self.patient_id = patient_id
        self.max_history = max_history
        self.postictal_grace_s = postictal_grace_s

        self.status: str = "stable"
        self.seizure_risk: float = 0.0
        self.seizure_type: Optional[str] = None
        self.active_region_meta: Optional[dict] = None

        self.regions: Dict[str, BrainRegionDef] = {k: BrainRegionDef(**v.__dict__) for k, v in BRAIN_REGIONS.items()}
        self._last_ictal_ts: Optional[float] = None
        self._last_update_ts: float = time.time()
        self.event_log: List[dict] = []

    def update(
        self, seizure_risk: float, seizure_type: Optional[str] = None,
        region_meta: Optional[dict] = None, lat: Optional[float] = None,
        lon: Optional[float] = None, channel_scores: Optional[dict] = None,
    ) -> dict:
        now = time.time()
        self._last_update_ts = now
        self.seizure_risk = float(seizure_risk)
        self.seizure_type = seizure_type

        new_status = self._compute_status(seizure_risk, now)
        self.status = new_status

        if new_status == "ictal":
            self._last_ictal_ts = now

        self._update_regions(seizure_risk, region_meta)

        alert_level = ALERT_LEVELS.get(new_status, "info")
        if seizure_risk >= BRAIN_STATUS_THRESHOLDS.get("elevated", 0.40):
            self.event_log.append({
                "timestamp": round(now, 3),
                "patient_id": self.patient_id,
                "brain_status": new_status,
                "seizure_risk": round(seizure_risk, 4),
                "seizure_type": seizure_type,
                "region_name": region_meta.get("region_name") if region_meta else None,
                "lobe": region_meta.get("lobe") if region_meta else None,
                "alert_level": alert_level,
                "notes": STATUS_LABELS.get(new_status, ""),
                "maps_link": _make_maps_link(lat, lon),
            })
            if len(self.event_log) > self.max_history:
                self.event_log = self.event_log[-self.max_history:]

        return self.snapshot(lat=lat, lon=lon)

    def _compute_status(self, risk: float, now: float) -> str:
        if risk >= BRAIN_STATUS_THRESHOLDS.get("ictal", 0.80):
            return "ictal"
        if (self._last_ictal_ts is not None and
                (now - self._last_ictal_ts) < self.postictal_grace_s):
            return "postictal"
        if risk >= BRAIN_STATUS_THRESHOLDS.get("preictal", 0.60):
            return "preictal"
        if risk >= BRAIN_STATUS_THRESHOLDS.get("elevated", 0.40):
            return "elevated"
        return "stable"

    def _update_regions(self, risk: float, region_meta: Optional[dict]) -> None:
        for r in self.regions.values():
            r.deactivate()
        if not region_meta or risk < BRAIN_STATUS_THRESHOLDS.get("elevated", 0.40):
            return
        region_name = region_meta.get("region_name")
        if region_name and region_name in self.regions:
            intensity = compute_highlight_intensity(risk)
            self.regions[region_name].activate(intensity=intensity)
            self.active_region_meta = region_meta

    def snapshot(self, lat: Optional[float] = None, lon: Optional[float] = None) -> dict:
        active_region_out = None
        for r in self.regions.values():
            if r.is_active and self.active_region_meta:
                active_region_out = {
                    **self.active_region_meta,
                    "highlight_intensity": round(r.activation, 4),
                    "color_current": r.current_color(),
                }
                break

        return {
            "patient_id": self.patient_id,
            "status": self.status,
            "status_label": STATUS_LABELS.get(self.status, ""),
            "status_color": STATUS_COLORS.get(self.status, "#6b7280"),
            "seizure_risk": round(self.seizure_risk, 4),
            "seizure_type": self.seizure_type,
            "alert_level": ALERT_LEVELS.get(self.status, "info"),
            "active_region": active_region_out,
            "regions": [r.to_dict() for r in self.regions.values()],
            "recent_events": self.event_log[-10:],
            "last_updated": round(self._last_update_ts, 3),
            "maps_link": _make_maps_link(lat, lon),
        }

    def reset(self) -> None:
        self.status = "stable"
        self.seizure_risk = 0.0
        self.seizure_type = None
        self.active_region_meta = None
        self._last_ictal_ts = None
        for r in self.regions.values():
            r.deactivate()


def _make_maps_link(lat: Optional[float], lon: Optional[float]) -> Optional[str]:
    if lat is not None and lon is not None:
        return f"https://maps.google.com/?q={lat},{lon}"
    return None


@dataclass
class SeizureAlert:
    alert_id: str
    patient_id: str
    timestamp: float
    alert_level: str
    brain_status: str
    seizure_risk: float
    seizure_type: Optional[str]
    region_name: Optional[str]
    lobe: Optional[str]
    lat: Optional[float]
    lon: Optional[float]
    fall_detected: bool
    message: str
    action: str
    maps_link: Optional[str]

    def to_dict(self) -> dict:
        return {
            "alert_id": self.alert_id, "patient_id": self.patient_id,
            "timestamp": self.timestamp, "alert_level": self.alert_level,
            "brain_status": self.brain_status,
            "seizure_risk": round(self.seizure_risk, 4),
            "seizure_type": self.seizure_type,
            "region_name": self.region_name, "lobe": self.lobe,
            "lat": self.lat, "lon": self.lon,
            "fall_detected": self.fall_detected,
            "message": self.message, "action": self.action,
            "maps_link": self.maps_link,
        }


class AlertManager:
    def __init__(self, patient_id: str, max_history: int = 50) -> None:
        self.patient_id = patient_id
        self.max_history = max_history
        self.history: List[SeizureAlert] = []
        self._alert_counter = 0

    def evaluate(
        self, brain_status: str, seizure_risk: float,
        seizure_type: Optional[str] = None, region_name: Optional[str] = None,
        lobe: Optional[str] = None, lat: Optional[float] = None,
        lon: Optional[float] = None, fall_detected: bool = False,
    ) -> Optional[SeizureAlert]:
        if brain_status == "stable":
            return None

        level = ALERT_LEVELS.get(brain_status, "info")
        risk_pct = f"{seizure_risk * 100:.1f}%"
        type_str = f" ({seizure_type})" if seizure_type and seizure_type != "Normal" else ""
        region_str = f" — Hypothesized zone: {region_name}" if region_name else ""
        fall_str = " FALL DETECTED" if fall_detected else ""
        message = (
            f"[{brain_status.upper()}] Seizure risk {risk_pct}{type_str}{region_str}{fall_str}. "
            f"DISCLAIMER: Region is estimated for demo purposes only."
        )

        if brain_status == "ictal" or fall_detected:
            action = "EMERGENCY: Alert caregiver immediately. Contact emergency services if patient unresponsive."
        elif brain_status == "preictal":
            action = "HIGH ALERT: Notify caregiver. Prepare for possible seizure. Move patient to safe position."
        elif brain_status == "elevated":
            action = "MONITOR: Increase observation frequency. Log activity."
        elif brain_status == "postictal":
            action = "RECOVERY: Keep patient safe. Do not restrain. Monitor breathing."
        else:
            action = "Continue monitoring."

        self._alert_counter += 1
        alert_id = f"{self.patient_id}-{int(time.time())}-{self._alert_counter:04d}"
        maps_link = f"https://maps.google.com/?q={lat},{lon}" if lat is not None and lon is not None else None

        alert = SeizureAlert(
            alert_id=alert_id, patient_id=self.patient_id,
            timestamp=time.time(), alert_level=level,
            brain_status=brain_status, seizure_risk=seizure_risk,
            seizure_type=seizure_type, region_name=region_name,
            lobe=lobe, lat=lat, lon=lon,
            fall_detected=fall_detected, message=message,
            action=action, maps_link=maps_link,
        )

        self.history.append(alert)
        if len(self.history) > self.max_history:
            self.history = self.history[-self.max_history:]
        return alert

    def latest_alert(self) -> Optional[SeizureAlert]:
        return self.history[-1] if self.history else None


# ==============================================================================
# NeuroInferenceEngine — Main Orchestrator
# ==============================================================================

class NeuroInferenceEngine:
    """
    Orchestrates the full NeurologiqueTWIN inference pipeline.

    Wires together signal processing, feature extraction, seizure prediction,
    multimodal fusion, digital twin state, brain region mapping, and alerts.
    """

    def __init__(self, config: Optional[NeurologiqueConfig] = None) -> None:
        self.config = config or NeurologiqueConfig()

        # Components
        self.eeg = EEGProcessor(
            fs=self.config.fs, lowcut=self.config.lowcut,
            highcut=self.config.highcut, notch_freq=self.config.notch_freq,
            epoch_len_s=self.config.epoch_len_s, overlap=self.config.overlap,
        )
        self.imu = IMUProcessor(
            fs_ppg=self.config.fs_ppg, fs_acc=self.config.fs_acc,
            fs_eda=self.config.fs_eda, hr_baseline=self.config.hr_baseline,
            eda_baseline=self.config.eda_baseline,
        )
        self.nlp = ClinicalNLPAnalyzer()
        self.transformer = TimeSeriesTransformer(
            image_size=self.config.image_size, n_bins=self.config.n_bins,
        )
        self.event_bus = EventBus()

        self.tabular = TabularSeizurePredictor(fs=self.config.fs)
        self.cnn_ensemble = EnsembleSeizurePredictor()
        self.scorer = ExplainableRiskScorer(
            ema_alpha=self.config.risk_ema_alpha,
            trend_boost=self.config.trend_boost,
            trend_window=self.config.trend_window,
        )
        self.fusion = MultimodalFusionEngine(weights=self.config.fusion_weights)
        self.digital_twin = DigitalTwin(
            predictor=self.tabular, bus=self.event_bus,
            risk_threshold=self.config.risk_threshold,
            history_len=self.config.history_len,
            alert_cooldown_s=self.config.alert_cooldown_s,
            min_consecutive=self.config.min_consecutive,
            ema_alpha=self.config.ema_alpha,
            deterministic=self.config.deterministic,
        )
        self.region_mapper = RegionMapper()

        # Patient-specific state
        self._patient_twins: Dict[str, BrainTwinState] = {}
        self._patient_alerts: Dict[str, AlertManager] = {}
        self._patient_risk_history: Dict[str, List[float]] = {}

    def get_or_create_twin(self, patient_id: str) -> BrainTwinState:
        if patient_id not in self._patient_twins:
            self._patient_twins[patient_id] = BrainTwinState(
                patient_id=patient_id,
                postictal_grace_s=self.config.postictal_grace_s,
            )
            self._patient_alerts[patient_id] = AlertManager(patient_id=patient_id)
            self._patient_risk_history[patient_id] = []
        return self._patient_twins[patient_id]

    def process_inference(
        self, patient_id: str, seizure_risk: float,
        seizure_type: Optional[str] = None,
        channel_scores: Optional[Dict[str, float]] = None,
        dominant_channels: Optional[List[str]] = None,
        lat: Optional[float] = None, lon: Optional[float] = None,
        fall_detected: bool = False,
        band_powers: Optional[Dict[str, float]] = None,
        eeg_energy: float = 0.0,
        raw_eeg: Optional[np.ndarray] = None,
        raw_ppg: Optional[np.ndarray] = None,
        raw_acc: Optional[np.ndarray] = None,
        raw_eda: Optional[np.ndarray] = None,
        clinical_text: Optional[str] = None,
    ) -> Dict[str, Any]:
        brain_state = self.get_or_create_twin(patient_id)
        alert_mgr = self._patient_alerts[patient_id]
        risk_history = self._patient_risk_history[patient_id]

        # Step 1: Process raw signals
        imu_features: Optional[WearableFeatures] = None
        if any(x is not None for x in [raw_ppg, raw_acc, raw_eda]):
            imu_features = self.imu.process(
                ppg=raw_ppg, acc=raw_acc, eda_raw=raw_eda,
            )

        nlp_result = None
        if clinical_text:
            nlp_result = self.nlp.analyze(clinical_text)

        # Step 2: Run predictors
        cnn_risk = self.cnn_ensemble({"rgb": None, **({"eeg_energy": eeg_energy} if eeg_energy else {})})
        xgboost_risk = self.tabular(
            {"eeg_energy": eeg_energy, **((imu_features.to_twin_features()) if imu_features else {})}
        )

        # Step 3: Explainable risk scoring
        scorer_features = {"eeg_energy": eeg_energy}
        if imu_features:
            scorer_features.update(imu_features.to_twin_features())
        explanation = self.scorer.explain(scorer_features)

        # Step 4: Digital twin step
        twin_result = self.digital_twin.step(scorer_features)

        # Step 5: NLP risk
        nlp_risk = float(nlp_result["risk_score"]) if nlp_result else None

        # Step 6: IMU composite risk
        imu_risk = None
        if imu_features:
            imu_risk = imu_features.stress_index

        # Step 7: Multimodal fusion
        fusion_result = self.fusion.fuse(
            cnn_risk=cnn_risk, xgboost_risk=xgboost_risk,
            nlp_risk=nlp_risk, imu_risk=imu_risk,
            twin_state=twin_result["state"],
        )

        # Step 8: Region mapping
        region_meta = self.region_mapper.resolve(
            seizure_risk=seizure_risk, seizure_type=seizure_type,
            channel_scores=channel_scores,
            dominant_channels=dominant_channels,
        )

        # Step 9: Brain state update
        twin_snapshot = brain_state.update(
            seizure_risk=seizure_risk, seizure_type=seizure_type,
            region_meta=region_meta, lat=lat, lon=lon,
            channel_scores=channel_scores,
        )

        # Step 10: Alert evaluation
        alert = alert_mgr.evaluate(
            brain_status=brain_state.status, seizure_risk=seizure_risk,
            seizure_type=seizure_type,
            region_name=region_meta.get("region_name"),
            lobe=region_meta.get("lobe"), lat=lat, lon=lon,
            fall_detected=fall_detected,
        )

        # Step 11: History
        risk_history.append(round(float(seizure_risk), 4))
        if len(risk_history) > self.config.max_history:
            risk_history[:] = risk_history[-self.config.max_history:]

        return {
            "patient_id": patient_id,
            "twin": twin_snapshot,
            "region": region_meta,
            "alert": alert.to_dict() if alert else None,
            "risk_history": risk_history[-20:],
            "seizure_type": seizure_type,
            "band_powers": band_powers or {},
            "eeg_energy": round(float(eeg_energy), 4),
            "fusion": {
                "final_risk": fusion_result.final_risk,
                "risk_level": fusion_result.risk_level,
                "confidence": fusion_result.confidence,
                "agreement": fusion_result.agreement,
                "dominant_modality": fusion_result.dominant_modality,
                "attribution": fusion_result.attribution,
                "clinical_summary": fusion_result.clinical_summary,
            },
            "explanation": {
                "seizure_risk": explanation.seizure_risk,
                "raw_risk": explanation.raw_risk,
                "risk_level": explanation.risk_level,
                "dominant_driver": explanation.dominant_driver,
                "clinical_note": explanation.clinical_note,
                "attribution": explanation.attribution_dict,
            },
        }

    def process_eeg(self, raw_eeg: np.ndarray) -> Dict[str, Any]:
        processed = self.eeg.process(raw_eeg)
        epochs = self.eeg.segment(processed)
        rgb = to_rgb(processed, self.config.image_size) if len(processed) > 32 else None
        return {
            "processed": processed,
            "n_epochs": len(epochs),
            "rgb_image": rgb,
            "spectral_energy": self.eeg.spectral_energy(processed) if len(processed) > 0 else 0.0,
            "band_powers": self.eeg.band_powers(processed) if len(processed) > 0 else {},
        }

    def process_imu_stream(
        self, ppg: Optional[np.ndarray] = None,
        acc: Optional[np.ndarray] = None,
        eda_raw: Optional[np.ndarray] = None,
    ) -> WearableFeatures:
        return self.imu.process(ppg=ppg, acc=acc, eda_raw=eda_raw)

    def analyze_text(self, text: str) -> Dict:
        return self.nlp.analyze(text)

    def get_patient_status(self, patient_id: str) -> Optional[Dict]:
        twin = self._patient_twins.get(patient_id)
        if twin is None:
            return None
        return {
            "twin": twin.snapshot(),
            "risk_history": self._patient_risk_history.get(patient_id, [])[-20:],
        }

    def list_patients(self) -> List[str]:
        return list(self._patient_twins.keys())

    def reset_patient(self, patient_id: str) -> bool:
        twin = self._patient_twins.get(patient_id)
        if twin:
            twin.reset()
            if patient_id in self._patient_risk_history:
                self._patient_risk_history[patient_id].clear()
            return True
        return False

    def get_status(self) -> Dict[str, Any]:
        return {
            "config": self.config.to_dict(),
            "patients": self.list_patients(),
            "digital_twin": {
                "state": self.digital_twin.state,
                "risk_ema": self.digital_twin.risk_ema,
            },
        }
