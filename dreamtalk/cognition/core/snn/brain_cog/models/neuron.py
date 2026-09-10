# Dreamtalk - Cognition Module
# Extracted from Brain-Cog (https://github.com/BrainCog-X/Brain-Cog)
# Author: Floyed <Floyed_Shen@outlook.com>
# License: MIT

import abc
import math
from abc import ABC

import torch
from torch import nn
from torch.nn import Parameter


class SurrogateGrad(torch.autograd.Function):
    @staticmethod
    def forward(ctx, x, alpha=2.0):
        ctx.save_for_backward(x, torch.tensor(alpha))
        return (x > 0).float()

    @staticmethod
    def backward(ctx, grad_output):
        x, alpha = ctx.saved_tensors
        grad_input = grad_output.clone()
        sg = 1.0 / (1.0 + alpha * x.abs()) ** 2
        return grad_input * sg, None


class BaseNode(nn.Module, abc.ABC):
    def __init__(
        self,
        threshold: float = 0.5,
        v_reset: float = 0.0,
        dt: float = 1.0,
        step: int = 8,
        requires_thres_grad: bool = False,
        sigmoid_thres: bool = False,
        requires_fp: bool = False,
        layer_by_layer: bool = False,
        n_groups: int = 1,
        mem_detach: bool = False,
        requires_mem: bool = False,
    ):
        super().__init__()
        self.threshold = Parameter(
            torch.tensor(threshold), requires_grad=requires_thres_grad
        )
        self.sigmoid_thres = sigmoid_thres
        self.mem = 0.0
        self.spike = 0.0
        self.dt = dt
        self.feature_map = []
        self.mem_collect = []
        self.requires_fp = requires_fp
        self.v_reset = v_reset
        self.step = step
        self.layer_by_layer = layer_by_layer
        self.groups = n_groups
        self.mem_detach = mem_detach
        self.requires_mem = requires_mem

    @abc.abstractmethod
    def calc_spike(self):
        pass

    def integral(self, inputs):
        pass

    def get_thres(self):
        return (
            self.threshold
            if not self.sigmoid_thres
            else self.threshold.sigmoid()
        )

    def forward(self, inputs):
        if self.mem_detach and hasattr(self.mem, "detach"):
            self.mem = self.mem.detach()
            self.spike = self.spike.detach()
        self.integral(inputs)
        self.calc_spike()
        if self.requires_fp:
            self.feature_map.append(self.spike)
        if self.requires_mem:
            self.mem_collect.append(self.mem)
        return self.spike

    def n_reset(self):
        self.mem = self.v_reset
        self.spike = 0.0
        self.feature_map = []
        self.mem_collect = []

    def set_n_threshold(self, thresh: float):
        self.threshold = Parameter(
            torch.tensor(thresh, dtype=torch.float), requires_grad=False
        )

    def set_n_tau(self, tau: float):
        if hasattr(self, "tau"):
            self.tau = Parameter(
                torch.tensor(tau, dtype=torch.float), requires_grad=False
            )


class IFNode(BaseNode):
    def __init__(self, threshold: float = 0.5, **kwargs):
        super().__init__(threshold, **kwargs)
        self.act_fun = SurrogateGrad.apply

    def integral(self, inputs):
        self.mem = self.mem + inputs * self.dt

    def calc_spike(self):
        self.spike = self.act_fun(self.mem - self.get_thres())
        self.mem = self.mem * (1 - self.spike.detach())


class LIFNode(BaseNode):
    def __init__(
        self, threshold: float = 0.5, tau: float = 2.0, **kwargs
    ):
        super().__init__(threshold, **kwargs)
        self.tau = tau
        self.act_fun = SurrogateGrad.apply

    def integral(self, inputs):
        self.mem = self.mem + (inputs - self.mem) / self.tau

    def calc_spike(self):
        self.spike = self.act_fun(self.mem - self.threshold)
        self.mem = self.mem * (1 - self.spike.detach())


class PLIFNode(BaseNode):
    def __init__(
        self, threshold: float = 1.0, tau: float = 2.0, **kwargs
    ):
        super().__init__(threshold, **kwargs)
        init_w = -math.log(tau - 1.0)
        self.act_fun = SurrogateGrad.apply
        self.w = nn.Parameter(torch.as_tensor(init_w))

    def integral(self, inputs):
        self.mem = self.mem + ((inputs - self.mem) * self.w.sigmoid()) * self.dt

    def calc_spike(self):
        self.spike = self.act_fun(self.mem - self.get_thres())
        self.mem = self.mem * (1 - self.spike.detach())


class IzhNode(BaseNode):
    def __init__(
        self,
        threshold: float = 1.0,
        tau: float = 2.0,
        a: float = 0.02,
        b: float = 0.2,
        c: float = -55.0,
        d: float = -2.0,
        **kwargs,
    ):
        super().__init__(threshold, **kwargs)
        self.tau = tau
        self.act_fun = SurrogateGrad.apply
        self.a = a
        self.b = b
        self.c = c
        self.d = d
        self.mem = 0.0
        self.u = 0.0

    def integral(self, inputs):
        self.mem = self.mem + self.dt * (
            0.04 * self.mem * self.mem + 5 * self.mem - self.u + 140 + inputs
        )
        self.u = self.u + self.dt * (self.a * self.b * self.mem - self.a * self.u)

    def calc_spike(self):
        self.spike = self.act_fun(self.mem - self.get_thres())
        self.mem = self.mem * (1 - self.spike.detach()) + self.spike.detach() * self.c
        self.u = self.u + self.spike.detach() * self.d

    def n_reset(self):
        self.mem = 0.0
        self.u = 0.0
        self.spike = 0.0


class LIFSTDPNode(BaseNode):
    def __init__(
        self, threshold: float = 1.0, tau: float = 2.0, **kwargs
    ):
        super().__init__(threshold, **kwargs)
        self.tau = tau
        self.act_fun = SurrogateGrad.apply

    def integral(self, inputs):
        self.mem = self.mem * self.tau + inputs

    def calc_spike(self):
        self.spike = self.act_fun(self.mem - self.threshold)
        self.mem = self.mem * (1 - self.spike.detach())

    def requires_activation(self):
        return False


class NoiseLIFNode(LIFNode):
    def __init__(
        self,
        threshold: float = 1.0,
        tau: float = 2.0,
        log_alpha: float = math.log(2),
        log_beta: float = math.log(6),
        **kwargs,
    ):
        super().__init__(threshold=threshold, tau=tau, **kwargs)
        self.log_alpha = Parameter(
            torch.as_tensor(log_alpha), requires_grad=True
        )
        self.log_beta = Parameter(
            torch.as_tensor(log_beta), requires_grad=True
        )

    def integral(self, inputs):
        alpha, beta = torch.exp(self.log_alpha), torch.exp(self.log_beta)
        noise = (
            torch.distributions.beta.Beta(alpha, beta)
            .sample(inputs.shape)
            .to(inputs.device)
            * self.get_thres()
        )
        self.mem = self.mem + ((inputs - self.mem) / self.tau + noise) * self.dt
