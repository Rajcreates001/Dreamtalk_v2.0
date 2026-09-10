# Dreamtalk - Cognition Module
# Extracted from Aura (https://github.com/anomalyco/aura)
# License: MIT
#
# IIT 4.0 Integrated Information Theory surrogate implementation.
# References:
#   - Albantakis et al. (2023) IIT 4.0. PLoS Comput Biol.
#   - Barrett & Seth (2011) PLoS Comp Bio
#   - Tononi (2014) Consciousness as integrated information. Biol Bull.

from __future__ import annotations

import logging
import math
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any

import numpy as np

logger = logging.getLogger("Dreamtalk.Consciousness")

_REGULARIZATION = 1e-6
_MIN_SAMPLES = 8


@dataclass
class PhiResult:
    phi_s: float
    mip_partition_a: list[int]
    mip_partition_b: list[int]
    mip_phi_value: float
    all_partition_phis: list[float]
    tpm_n_samples: int
    computed_at: float = field(default_factory=time.time)

    @property
    def is_complex(self) -> bool:
        return self.phi_s > 1e-6


@dataclass
class PhiConfig:
    trajectory_length: int = 200
    sample_interval: int = 1
    regularization: float = 1e-6
    max_exhaustive_n: int = 16
    kl_refinement_swaps: int = 50
    min_partition_size: int = 1
    seed: int = 91


class RIIU:
    def __init__(
        self,
        neuron_count: int = 64,
        buffer_size: int = 64,
        num_partitions: int = 16,
    ):
        self.neuron_count = neuron_count
        self.buffer_size = buffer_size
        self.num_partitions = num_partitions
        self.network_dim = 128
        self.total_dim = neuron_count + self.network_dim
        self._buffer = np.zeros(
            (buffer_size, self.total_dim), dtype=np.float64
        )
        self._write_idx = 0
        self._samples_collected = 0
        self._last_phi: float = 0.0
        self._last_whole_logdet: float = 0.0
        self._tick_count: int = 0
        self._warmup = True
        self._partitions = self._generate_partitions()

    def compute_phi(self, state_vector: np.ndarray) -> float:
        v = np.zeros(self.total_dim, dtype=np.float64)
        n = min(len(state_vector), self.total_dim)
        v[:n] = state_vector[:n]
        self._buffer[self._write_idx] = v
        self._write_idx = (self._write_idx + 1) % self.buffer_size
        self._samples_collected = min(
            self.buffer_size, self._samples_collected + 1
        )
        self._tick_count += 1
        phi = self._last_phi
        if self._samples_collected >= _MIN_SAMPLES:
            self._warmup = False
            if self._tick_count % 5 == 0:
                data = self._buffer[: self._samples_collected]
                phi = self._compute_phi_internal(data)
        else:
            self._warmup = True
            phi = 0.0
        self._last_phi = phi
        return phi

    def get_phi(self) -> float:
        return self._last_phi

    def get_stats(self) -> dict:
        return {
            "phi": round(self._last_phi, 6),
            "whole_logdet": round(self._last_whole_logdet, 6),
            "samples": self._samples_collected,
            "buffer_full": self._samples_collected >= self.buffer_size,
            "warmup": self._warmup,
        }

    def _compute_phi_internal(self, data: np.ndarray) -> float:
        n_samples, n_dims = data.shape
        cov_whole = self._regularized_covariance(data)
        try:
            sign_w, logdet_w = np.linalg.slogdet(cov_whole)
        except (RuntimeError, ValueError, np.linalg.LinAlgError):
            return 0.0
        if sign_w <= 0 or not np.isfinite(logdet_w):
            return 0.0
        self._last_whole_logdet = logdet_w
        min_partition_logdet = np.inf
        for part_a, part_b in self._partitions:
            if len(part_a) < 2 or len(part_b) < 2:
                continue
            cov_a = self._regularized_covariance(data[:, part_a])
            cov_b = self._regularized_covariance(data[:, part_b])
            try:
                sign_a, logdet_a = np.linalg.slogdet(cov_a)
                sign_b, logdet_b = np.linalg.slogdet(cov_b)
            except (RuntimeError, ValueError, np.linalg.LinAlgError):
                continue
            if sign_a <= 0 or sign_b <= 0:
                continue
            if not np.isfinite(logdet_a) or not np.isfinite(logdet_b):
                continue
            partition_logdet = logdet_a + logdet_b
            if not np.isfinite(partition_logdet):
                continue
            min_partition_logdet = min(min_partition_logdet, partition_logdet)
        if min_partition_logdet == np.inf:
            return 0.0
        phi = min_partition_logdet - logdet_w
        if not np.isfinite(phi):
            return 0.0
        return float(np.clip(phi, 0.0, 1000.0))

    def _regularized_covariance(self, data: np.ndarray) -> np.ndarray:
        cov = np.cov(data, rowvar=False)
        if cov.ndim == 0:
            cov = np.array([[float(cov)]])
        cov += np.eye(cov.shape[0]) * _REGULARIZATION
        return cov

    def _generate_partitions(self):
        indices = np.arange(self.total_dim)
        partitions = []
        rng = np.random.RandomState(42)
        for _ in range(self.num_partitions):
            split = rng.randint(
                self.total_dim // 2 - 4, self.total_dim // 2 + 5
            )
            perm = rng.permutation(indices)
            part_a = sorted(perm[:split].tolist())
            part_b = sorted(perm[split:].tolist())
            partitions.append((part_a, part_b))
        return partitions


class PhiComputer:
    def __init__(self, config: PhiConfig | None = None):
        self.config = config or PhiConfig()
        self._rng = np.random.default_rng(self.config.seed)
        self._trajectory: deque = deque(
            maxlen=self.config.trajectory_length
        )
        self._step_counter = 0
        self._last_result: PhiResult | None = None
        self._phi_history: deque = deque(maxlen=100)

    def record_state(self, state: np.ndarray) -> None:
        self._step_counter += 1
        if self._step_counter % self.config.sample_interval == 0:
            self._trajectory.append(
                np.asarray(state, dtype=np.float64).ravel().copy()
            )

    @property
    def has_sufficient_data(self) -> bool:
        return len(self._trajectory) >= max(
            20, self._trajectory.maxlen // 2
        )

    def compute(
        self, coupling_matrix: np.ndarray | None = None
    ) -> PhiResult:
        t_start = time.monotonic()
        if not self.has_sufficient_data:
            raise ValueError(
                f"Insufficient data: {len(self._trajectory)} samples"
            )
        states = np.array(list(self._trajectory), dtype=np.float64)
        T, N = states.shape
        if N < 2:
            return PhiResult(
                phi_s=0.0,
                mip_partition_a=[],
                mip_partition_b=[],
                mip_phi_value=0.0,
                all_partition_phis=[],
                tpm_n_samples=T,
            )
        cov = np.cov(states.T)
        if cov.ndim == 0:
            cov = np.array([[float(cov)]])
        cov += self.config.regularization * np.eye(cov.shape[0])
        sys_entropy = self._gaussian_entropy(cov)
        if N <= self.config.max_exhaustive_n:
            result = self._exhaustive_phi(cov, sys_entropy, N)
        else:
            result = self._spectral_phi(
                cov, sys_entropy, N, coupling_matrix
            )
        result.computed_at = time.monotonic()
        self._last_result = result
        self._phi_history.append(result.phi_s)
        return result

    @staticmethod
    def _gaussian_entropy(cov: np.ndarray) -> float:
        n = cov.shape[0]
        try:
            L = np.linalg.cholesky(cov)
            log_det = 2.0 * np.sum(np.log(np.diag(L)))
        except np.linalg.LinAlgError:
            eigvals = np.linalg.eigvalsh(cov)
            eigvals = np.maximum(eigvals, 1e-15)
            log_det = float(np.sum(np.log(eigvals)))
        return float(
            0.5 * (n * np.log(2 * np.pi * np.e) + log_det)
        )

    def _exhaustive_phi(
        self, cov: np.ndarray, sys_h: float, N: int
    ) -> PhiResult:
        min_phi = float("inf")
        best_a: list[int] = []
        best_b: list[int] = []
        n_eval = 0
        ms = self.config.min_partition_size
        indices = list(range(N))
        for mask in range(1, 2**N - 1):
            a = [i for i in indices if mask & (1 << i)]
            b = [i for i in indices if not (mask & (1 << i))]
            if len(a) < ms or len(b) < ms:
                continue
            if len(a) > len(b) or (len(a) == len(b) and a[0] > b[0]):
                continue
            phi = self._phi_for_partition(cov, sys_h, a, b)
            n_eval += 1
            if phi < min_phi:
                min_phi = phi
                best_a, best_b = a, b
        if min_phi == float("inf"):
            min_phi = 0.0
        return PhiResult(
            phi_s=min_phi,
            mip_partition_a=best_a,
            mip_partition_b=best_b,
            mip_phi_value=min_phi,
            all_partition_phis=[],
            tpm_n_samples=n_eval,
        )

    def _spectral_phi(
        self,
        cov: np.ndarray,
        sys_h: float,
        N: int,
        coupling: np.ndarray | None = None,
    ) -> PhiResult:
        adj = (
            np.abs(coupling)
            if coupling is not None and coupling.shape == (N, N)
            else np.abs(cov)
        )
        np.fill_diagonal(adj, 0.0)
        degree = np.sum(adj, axis=1)
        laplacian = np.diag(degree) - adj
        d_inv = np.zeros_like(degree)
        nz = degree > 1e-10
        d_inv[nz] = 1.0 / np.sqrt(degree[nz])
        L_norm = np.diag(d_inv) @ laplacian @ np.diag(d_inv)
        eigvals, eigvecs = np.linalg.eigh(L_norm)
        fiedler = eigvecs[:, min(1, N - 1)]
        a = [i for i in range(N) if fiedler[i] >= 0]
        b = [i for i in range(N) if fiedler[i] < 0]
        ms = self.config.min_partition_size
        while len(a) < ms and b:
            a.append(b.pop())
        while len(b) < ms and a:
            b.append(a.pop())
        best_phi = self._phi_for_partition(cov, sys_h, a, b)
        for _ in range(self.config.kl_refinement_swaps):
            improved = False
            for ii in range(len(a)):
                for jj in range(len(b)):
                    ta, tb = a.copy(), b.copy()
                    ta[ii], tb[jj] = tb[jj], ta[ii]
                    if len(ta) < ms or len(tb) < ms:
                        continue
                    tp = self._phi_for_partition(cov, sys_h, ta, tb)
                    if tp < best_phi:
                        best_phi, a, b = tp, ta, tb
                        improved = True
                        break
                if improved:
                    break
            if not improved:
                break
        a.sort()
        b.sort()
        return PhiResult(
            phi_s=best_phi,
            mip_partition_a=a,
            mip_partition_b=b,
            mip_phi_value=best_phi,
            all_partition_phis=[],
            tpm_n_samples=1,
        )

    def _phi_for_partition(
        self, cov: np.ndarray, sys_h: float, a: list[int], b: list[int]
    ) -> float:
        if not a or not b:
            return 0.0
        h_a = self._gaussian_entropy(cov[np.ix_(a, a)])
        h_b = self._gaussian_entropy(cov[np.ix_(b, b)])
        return max(0.0, h_a + h_b - sys_h)

    @property
    def latest_phi(self) -> float:
        return self._last_result.phi_s if self._last_result else 0.0

    def get_status(self) -> dict[str, Any]:
        return {
            "trajectory_length": len(self._trajectory),
            "has_sufficient_data": self.has_sufficient_data,
            "latest_phi": round(self.latest_phi, 6),
        }


class PhiCore:
    COMPLEX_NODE_NAMES = [
        "valence", "arousal", "dominance", "frustration",
        "curiosity", "energy", "focus", "coherence",
        "phi", "social_hunger", "prediction_error",
        "agency_score", "narrative_tension",
        "peripheral_richness", "arousal_gate",
        "cross_timescale_fe",
    ]
    N_NODES = 16
    N_STATES = 65536

    def __init__(self):
        self._state_history: deque = deque(maxlen=2000)
        self._node_value_history: list[deque] = [
            deque(maxlen=100) for _ in range(self.N_NODES)
        ]
        self._running_medians: np.ndarray = np.zeros(
            self.N_NODES, dtype=np.float32
        )
        self._state_visits: np.ndarray = np.ones(
            self.N_STATES, dtype=np.float32
        )
        self._last_result: PhiResult | None = None
        self._last_compute_time: float = 0.0
        self._surrogate_phi: float = 0.0

    def record_state(
        self,
        substrate_x: np.ndarray,
        cognitive_values: dict[str, float] | None = None,
    ):
        if len(substrate_x) < 8:
            return
        affective = substrate_x[:8]
        cog = cognitive_values or {}
        cognitive = np.array(
            [
                cog.get("phi", 0.0),
                cog.get("social_hunger", 0.0),
                cog.get("prediction_error", 0.0),
                cog.get("agency_score", 0.0),
                cog.get("narrative_tension", 0.0),
                cog.get("peripheral_richness", 0.0),
                cog.get("arousal_gate", 0.0),
                cog.get("cross_timescale_fe", 0.0),
            ],
            dtype=np.float64,
        )
        x = np.concatenate([affective[:8], cognitive])
        for i, val in enumerate(x):
            self._node_value_history[i].append(float(val))
        for i in range(self.N_NODES):
            if len(self._node_value_history[i]) >= 3:
                self._running_medians[i] = float(
                    np.median(list(self._node_value_history[i]))
                )
        binary = (x > self._running_medians).astype(int)
        state_int = int(
            sum(int(b) << i for i, b in enumerate(binary))
        )
        self._state_history.append(state_int)
        self._state_visits[state_int] += 1.0

    def compute_surrogate_phi(self) -> float:
        if len(self._state_history) < 50:
            return 0.0
        history = list(self._state_history)
        cov = np.zeros((self.N_NODES, self.N_NODES), dtype=np.float64)
        for src in range(self.N_NODES):
            for dst in range(self.N_NODES):
                joint = np.zeros((2, 2), dtype=np.float64)
                for t in range(len(history) - 1):
                    src_val = (history[t] >> src) & 1
                    dst_val = (history[t + 1] >> dst) & 1
                    joint[src_val, dst_val] += 1.0
                total = joint.sum()
                if total < 1.0:
                    continue
                joint /= total
                p_src = joint.sum(axis=1)
                p_dst = joint.sum(axis=0)
                mi = 0.0
                for a in range(2):
                    for b in range(2):
                        if (
                            joint[a, b] > 1e-12
                            and p_src[a] > 1e-12
                            and p_dst[b] > 1e-12
                        ):
                            mi += joint[a, b] * np.log2(
                                joint[a, b] / (p_src[a] * p_dst[b])
                            )
                cov[src, dst] = max(0.0, mi)
        return float(np.trace(cov) / (self.N_NODES + 1e-10))

    def get_status(self) -> dict[str, Any]:
        return {
            "phi_surrogate": round(self._surrogate_phi, 6),
            "history_length": len(self._state_history),
            "node_count": self.N_NODES,
        }
