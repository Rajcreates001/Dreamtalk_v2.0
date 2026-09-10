# Dreamtalk - Cognition Module
# Extracted from NeurologiqueTWIN (https://github.com/anomalyco/NeurologiqueTWIN)
# License: MIT

from __future__ import annotations

from typing import Any, Dict, List, Optional

import numpy as np

from dreamtalk.cognition.core.neurological.neurologique.config import (
    NeurologiqueConfig,
    DEFAULT_CONFIG,
)
from dreamtalk.cognition.core.neurological.neurologique.inference import (
    NeuroInferenceEngine,
    DigitalTwin,
    MultimodalFusionEngine,
    ExplainableRiskScorer,
    RegionMapper,
    BrainTwinState,
    AlertManager,
    SeizureAlert,
    EventBus,
    TabularSeizurePredictor,
    EnsembleSeizurePredictor,
    EEGFeatureExtractor,
    FusionResult,
    RiskExplanation,
)
from dreamtalk.cognition.core.neurological.neurologique.models.eeg_processor import (
    EEGProcessor,
    TimeSeriesTransformer,
    gasf, mtf, recurrence_plot, to_rgb,
)
from dreamtalk.cognition.core.neurological.neurologique.models.imu_processor import (
    IMUProcessor,
    WearableFeatures,
)
from dreamtalk.cognition.core.neurological.neurologique.models.nlp_analyzer import (
    ClinicalNLPAnalyzer,
)


class NeurologiqueAPI:
    """
    High-level API for the NeurologiqueTWIN cognition module.

    Provides access to all signal processing, prediction, fusion,
    digital twin, region mapping, and alert components.
    """

    def __init__(self, config: NeurologiqueConfig | None = None):
        self.config = config or DEFAULT_CONFIG
        self.inference_engine = NeuroInferenceEngine(self.config)

    # ------------------------------------------------------------------
    # EEG
    # ------------------------------------------------------------------

    def process_eeg(self, raw_eeg: np.ndarray) -> Dict[str, Any]:
        return self.inference_engine.process_eeg(raw_eeg)

    def get_band_powers(self, epoch: np.ndarray) -> Dict[str, float]:
        return self.inference_engine.eeg.band_powers(epoch)

    def get_spectral_energy(self, epoch: np.ndarray) -> float:
        return self.inference_engine.eeg.spectral_energy(epoch)

    # ------------------------------------------------------------------
    # EEG Transforms (GASF, MTF, RP, RGB)
    # ------------------------------------------------------------------

    def to_gasf(self, signal: np.ndarray) -> np.ndarray:
        return gasf(signal, self.config.image_size)

    def to_mtf(self, signal: np.ndarray) -> np.ndarray:
        return mtf(signal, self.config.image_size, self.config.n_bins)

    def to_recurrence_plot(self, signal: np.ndarray) -> np.ndarray:
        return recurrence_plot(signal, self.config.image_size)

    def to_rgb(self, signal: np.ndarray) -> np.ndarray:
        return to_rgb(signal, self.config.image_size, self.config.n_bins)

    # ------------------------------------------------------------------
    # IMU / Wearable
    # ------------------------------------------------------------------

    def process_imu(
        self, ppg: Optional[np.ndarray] = None,
        acc: Optional[np.ndarray] = None,
        eda_raw: Optional[np.ndarray] = None,
    ) -> WearableFeatures:
        return self.inference_engine.process_imu_stream(ppg, acc, eda_raw)

    # ------------------------------------------------------------------
    # NLP
    # ------------------------------------------------------------------

    def analyze_text(self, text: str) -> Dict[str, Any]:
        return self.inference_engine.analyze_text(text)

    def batch_analyze_text(self, texts: List[str]) -> List[Dict[str, Any]]:
        return self.inference_engine.nlp.batch_analyze(texts)

    def get_nlp_finetune_guide(self) -> Dict[str, Any]:
        return ClinicalNLPAnalyzer.fine_tuning_guide()

    # ------------------------------------------------------------------
    # Predictors
    # ------------------------------------------------------------------

    def predict_tabular(
        self, eeg: Optional[np.ndarray] = None,
        imu: Optional[Dict[str, float]] = None,
    ) -> float:
        return self.inference_engine.tabular.predict(eeg=eeg, imu=imu)

    def predict_tabular_with_features(
        self, eeg: Optional[np.ndarray] = None,
        imu: Optional[Dict[str, float]] = None,
    ) -> Dict[str, Any]:
        feat = self.inference_engine.tabular.extractor.extract(eeg, imu)
        prob = self.inference_engine.tabular.predict(eeg=eeg, imu=imu)
        return {
            "seizure_probability": prob,
            "feature_vector": {
                name: float(val)
                for name, val in zip(
                    self.inference_engine.tabular.extractor.__class__.__module__,
                    feat,
                )
            },
        }

    def predict_ensemble(self, features: Dict) -> float:
        return self.inference_engine.cnn_ensemble(features)

    # ------------------------------------------------------------------
    # Explainable Scoring
    # ------------------------------------------------------------------

    def score_risk(self, features: Dict[str, float]) -> float:
        return self.inference_engine.scorer.score(features)

    def explain_risk(self, features: Dict[str, float]) -> RiskExplanation:
        return self.inference_engine.scorer.explain(features)

    # ------------------------------------------------------------------
    # Multimodal Fusion
    # ------------------------------------------------------------------

    def fuse(
        self, cnn_risk: Optional[float] = None,
        xgboost_risk: Optional[float] = None,
        nlp_risk: Optional[float] = None,
        imu_risk: Optional[float] = None,
        twin_state: Optional[str] = None,
    ) -> FusionResult:
        return self.inference_engine.fusion.fuse(
            cnn_risk, xgboost_risk, nlp_risk, imu_risk, twin_state,
        )

    # ------------------------------------------------------------------
    # Full Inference Pipeline
    # ------------------------------------------------------------------

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
        return self.inference_engine.process_inference(
            patient_id=patient_id, seizure_risk=seizure_risk,
            seizure_type=seizure_type,
            channel_scores=channel_scores,
            dominant_channels=dominant_channels,
            lat=lat, lon=lon, fall_detected=fall_detected,
            band_powers=band_powers, eeg_energy=eeg_energy,
            raw_eeg=raw_eeg, raw_ppg=raw_ppg, raw_acc=raw_acc,
            raw_eda=raw_eda, clinical_text=clinical_text,
        )

    # ------------------------------------------------------------------
    # Region Mapping
    # ------------------------------------------------------------------

    def resolve_region(
        self, seizure_risk: float = 0.0,
        seizure_type: Optional[str] = None,
        channel_scores: Optional[Dict[str, float]] = None,
        dominant_channels: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        return self.inference_engine.region_mapper.resolve(
            seizure_risk=seizure_risk, seizure_type=seizure_type,
            channel_scores=channel_scores,
            dominant_channels=dominant_channels,
        )

    # ------------------------------------------------------------------
    # Patient / Twin Management
    # ------------------------------------------------------------------

    def get_patient_status(self, patient_id: str) -> Optional[Dict]:
        return self.inference_engine.get_patient_status(patient_id)

    def list_patients(self) -> List[str]:
        return self.inference_engine.list_patients()

    def reset_patient(self, patient_id: str) -> bool:
        return self.inference_engine.reset_patient(patient_id)

    # ------------------------------------------------------------------
    # Event Bus
    # ------------------------------------------------------------------

    def get_events(self) -> List[Dict]:
        return [{"id": e.id, "type": e.type, "payload": e.payload}
                for e in self.inference_engine.event_bus.drain()]

    def subscribe(self, type_: str, callback):
        self.inference_engine.event_bus.subscribe(type_, callback)

    # ------------------------------------------------------------------
    # System
    # ------------------------------------------------------------------

    def get_status(self) -> Dict[str, Any]:
        return self.inference_engine.get_status()

    def reset(self) -> None:
        self.inference_engine.digital_twin.reset()
        self.inference_engine.scorer.reset()
