import torch
from typing import Any, Dict, List, Optional, Union

from .config import BrainCogConfig, DEFAULT_CONFIG
from .inference import SNNInferenceEngine
from .models.neuron import (
    BaseNode, IFNode, LIFNode, PLIFNode, IzhNode,
    LIFSTDPNode, NoiseLIFNode, SurrogateGrad,
)
from .models.learning import (
    STDP, MutliInputSTDP, LTP, LTD, FullSTDP, Hebb, BCM,
)
from .models.perception import (
    VotingLayer, WTALayer, SNNConvLayer, SNNLinearLayer, SNNEncoder,
)

NEURON_REGISTRY = {
    "if": IFNode,
    "lif": LIFNode,
    "plif": PLIFNode,
    "izh": IzhNode,
    "lif_stdp": LIFSTDPNode,
    "noise_lif": NoiseLIFNode,
}

LEARNING_REGISTRY = {
    "stdp": STDP,
    "multi_stdp": MutliInputSTDP,
    "ltp": LTP,
    "ltd": LTD,
    "full_stdp": FullSTDP,
    "hebb": Hebb,
    "bcm": BCM,
}

ENCODING_REGISTRY = {
    "poisson": "poisson",
    "temporal": "temporal",
    "population": "population",
    "phase": "phase",
    "rate": "rate",
}

ENCODING_DESCRIPTIONS = {
    "poisson": "Poisson spike train encoding based on input intensity",
    "temporal": "Temporal coding where spike time encodes value",
    "population": "Population coding across a group of neurons",
    "phase": "Phase-based encoding relative to oscillatory cycle",
    "rate": "Rate coding based on firing rate proportional to input",
}

COGNITIVE_FUNCTIONS = {
    "decision_making": "Evidence accumulation and decision output",
    "working_memory": "Maintain information over delay periods",
    "spatial_navigation": "Grid and place cell coding for navigation",
    "associative_learning": "Stimulus-response association via STDP",
    "attention": "Selective attention via top-down modulation",
    "sequence_learning": "Learning temporal sequences of spikes",
}

COGNITIVE_DOMAINS = {
    "perception": ["visual_cortex", "auditory_cortex", "somatosensory"],
    "memory": ["hippocampus", "prefrontal_cortex", "working_memory"],
    "motor": ["motor_cortex", "basal_ganglia", "cerebellum"],
    "decision": ["prefrontal_cortex", "anterior_cingulate", "striatum"],
    "emotion": ["amygdala", "orbitofrontal_cortex", "insula"],
}


class BrainCogAPI:
    def __init__(self, config: Optional[BrainCogConfig] = None):
        self.config = config or DEFAULT_CONFIG
        self.inference_engine = SNNInferenceEngine(self.config)
        self._networks: Dict[str, torch.nn.Module] = {}

    def neuron_types_available(self) -> Dict[str, str]:
        return {
            "if": "Integrate-and-Fire: simplest spiking neuron",
            "lif": "Leaky Integrate-and-Fire: membrane potential leaks over time",
            "plif": "Parametric LIF: learnable membrane time constant",
            "izh": "Izhikevich: rich dynamics (regular/fast spiking, bursting, chattering)",
            "lif_stdp": "LIF optimized for STDP learning (no activation function)",
            "noise_lif": "LIF with Beta-distributed noise injection for stochastic dynamics",
        }

    def create_neuron(self, neuron_type: str = "lif", **kwargs) -> torch.nn.Module:
        merged = {**self.config.to_dict(), **kwargs}
        cls = NEURON_REGISTRY.get(neuron_type.lower())
        if cls is None:
            raise ValueError(
                f"Unknown neuron type: {neuron_type}. "
                f"Available: {list(NEURON_REGISTRY.keys())}"
            )
        return cls(**merged)

    def create_learning_rule(self, rule_type: str = "stdp", **kwargs) -> torch.nn.Module:
        cls = LEARNING_REGISTRY.get(rule_type.lower())
        if cls is None:
            raise ValueError(
                f"Unknown learning rule: {rule_type}. "
                f"Available: {list(LEARNING_REGISTRY.keys())}"
            )
        return cls(**kwargs)

    def encoding_methods_available(self) -> Dict[str, str]:
        return dict(ENCODING_DESCRIPTIONS)

    def encode(self, data: torch.Tensor, encoding: str = "poisson") -> torch.Tensor:
        encoder = SNNEncoder(encoding=encoding, step=self.config.step)
        return encoder(data)

    def create_conv_layer(self, in_channels: int, out_channels: int, kernel_size: int = 3,
                          stride: int = 1, padding: int = 1, neuron_type: str = "lif",
                          threshold: float = 0.5, tau: float = 2.0) -> SNNConvLayer:
        return SNNConvLayer(
            in_channels, out_channels, kernel_size, stride, padding,
            neuron_type=neuron_type, threshold=threshold, tau=tau,
            step=self.config.step,
        )

    def create_linear_layer(self, in_features: int, out_features: int,
                            neuron_type: str = "lif", threshold: float = 0.5,
                            tau: float = 2.0) -> SNNLinearLayer:
        return SNNLinearLayer(
            in_features, out_features,
            neuron_type=neuron_type, threshold=threshold, tau=tau,
            step=self.config.step,
        )

    def create_voting_layer(self, voter_num: int) -> VotingLayer:
        return VotingLayer(voter_num)

    def create_wta_layer(self, k: int = 1) -> WTALayer:
        return WTALayer(k)

    def cognitive_functions_available(self) -> Dict[str, str]:
        return dict(COGNITIVE_FUNCTIONS)

    def cognitive_domains_available(self) -> Dict[str, List[str]]:
        return dict(COGNITIVE_DOMAINS)

    def register_network(self, name: str, network: torch.nn.Module):
        self._networks[name] = network
        self.inference_engine.load_network(network, name)

    def run_network(self, name: str, input_data: torch.Tensor) -> torch.Tensor:
        if name not in self._networks:
            raise ValueError(f"Network '{name}' not registered. Registered: {list(self._networks.keys())}")
        return self.inference_engine.run_inference(self._networks[name], input_data)

    def build_dmn_network(self, input_size: int = 100, hidden_size: int = 64,
                          output_size: int = 2) -> torch.nn.Module:
        class DecisionMakingNetwork(torch.nn.Module):
            def __init__(self, api, input_sz, hidden_sz, output_sz):
                super().__init__()
                self.input = api.create_linear_layer(input_sz, hidden_sz, neuron_type="lif")
                self.hidden = api.create_linear_layer(hidden_sz, hidden_sz, neuron_type="lif")
                self.output = api.create_linear_layer(hidden_sz, output_sz, neuron_type="if")
                self.wta = api.create_wta_layer(k=1)

            def forward(self, x):
                x = self.input(x)
                x = self.hidden(x)
                x = self.output(x)
                x = self.wta(x)
                return x

        net = DecisionMakingNetwork(self, input_size, hidden_size, output_size)
        self.register_network("decision_making", net)
        return net

    def build_wm_network(self, input_size: int = 50, delay_size: int = 32,
                         output_size: int = 10) -> torch.nn.Module:
        class WorkingMemoryNetwork(torch.nn.Module):
            def __init__(self, api, input_sz, delay_sz, output_sz):
                super().__init__()
                self.input_proj = api.create_linear_layer(input_sz, delay_sz, neuron_type="lif")
                self.recurrent = api.create_linear_layer(delay_sz, delay_sz, neuron_type="lif", tau=4.0)
                self.output = api.create_linear_layer(delay_sz, output_sz, neuron_type="if")

            def forward(self, x):
                x = self.input_proj(x)
                for _ in range(5):
                    x = self.recurrent(x)
                x = self.output(x)
                return x

        net = WorkingMemoryNetwork(self, input_size, delay_size, output_size)
        self.register_network("working_memory", net)
        return net

    def get_status(self) -> Dict[str, Any]:
        return {
            "config": self.config.to_dict(),
            "device": str(self.inference_engine.device),
            "neuron_types": list(NEURON_REGISTRY.keys()),
            "learning_rules": list(LEARNING_REGISTRY.keys()),
            "encoding_methods": list(ENCODING_REGISTRY.keys()),
            "cognitive_functions": list(COGNITIVE_FUNCTIONS.keys()),
            "cognitive_domains": list(COGNITIVE_DOMAINS.keys()),
            "registered_networks": list(self._networks.keys()),
        }
