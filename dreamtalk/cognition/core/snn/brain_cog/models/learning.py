# Dreamtalk - Cognition Module
# Extracted from Brain-Cog (https://github.com/BrainCog-X/Brain-Cog)
# License: MIT

import torch
from torch import nn
from torch.nn import Parameter

from dreamtalk.cognition.core.snn.brain_cog.models.neuron import BaseNode


class STDP(nn.Module):
    def __init__(
        self, node: BaseNode, connection: nn.Module, decay: float = 0.99
    ):
        super().__init__()
        self.node = node
        self.connection = connection
        self.trace = None
        self.decay = decay

    def forward(self, x):
        x = x.clone().detach()
        i = self.connection(x)
        with torch.no_grad():
            s = self.node(i)
            i.data += s - i.data
            trace = self.cal_trace(x)
            x.data += trace - x.data
        dw = torch.autograd.grad(
            outputs=i,
            inputs=self.connection.weight,
            grad_outputs=i,
        )
        return s, dw

    def cal_trace(self, x):
        if self.trace is None:
            self.trace = Parameter(x.clone().detach(), requires_grad=False)
        else:
            self.trace *= self.decay
            self.trace += x
        return self.trace.detach()

    def reset(self):
        self.trace = None


class MutliInputSTDP(nn.Module):
    def __init__(
        self, node: BaseNode, connection: list[nn.Module], decay: float = 0.99
    ):
        super().__init__()
        self.node = node
        self.connection = connection
        self.trace = [None for _ in self.connection]
        self.decay = decay

    def forward(self, *x):
        i = 0
        x = [xi.clone().detach() for xi in x]
        for xi, coni in zip(x, self.connection):
            i += coni(xi)
        with torch.no_grad():
            s = self.node(i)
            i.data += s - i.data
            trace = self.cal_trace(x)
            for xi, ti in zip(x, trace):
                xi.data += ti - xi.data
        dw = torch.autograd.grad(
            outputs=i,
            inputs=[c.weight for c in self.connection],
            grad_outputs=i,
        )
        return s, dw

    def cal_trace(self, x):
        for i in range(len(x)):
            if self.trace[i] is None:
                self.trace[i] = Parameter(
                    x[i].clone().detach(), requires_grad=False
                )
            else:
                self.trace[i] *= self.decay
                self.trace[i] += x[i].detach()
        return self.trace

    def reset(self):
        self.trace = [None for _ in self.connection]


class LTP(MutliInputSTDP):
    pass


class LTD(nn.Module):
    def __init__(
        self, node: BaseNode, connection: list[nn.Module], decay: float = 0.99
    ):
        super().__init__()
        self.node = node
        self.connection = connection
        self.trace = None
        self.decay = decay

    def forward(self, *x):
        i = 0
        x = [xi.clone().detach() for xi in x]
        for xi, coni in zip(x, self.connection):
            i += coni(xi)
        with torch.no_grad():
            s = self.node(i)
            trace = self.cal_trace(s)
            i.data += trace - i.data
        dw = torch.autograd.grad(
            outputs=i,
            inputs=[c.weight for c in self.connection],
            grad_outputs=i,
        )
        return s, dw

    def cal_trace(self, x):
        if self.trace is None:
            self.trace = Parameter(torch.zeros_like(x), requires_grad=False)
        else:
            self.trace *= self.decay
        trace = self.trace.clone().detach()
        self.trace += x
        return trace

    def reset(self):
        self.trace = None


class FullSTDP(nn.Module):
    def __init__(
        self,
        node: BaseNode,
        connection: list[nn.Module],
        decay: float = 0.99,
        decay2: float = 0.99,
    ):
        super().__init__()
        self.node = node
        self.connection = connection
        self.tracein = [None for _ in self.connection]
        self.traceout = None
        self.decay = decay
        self.decay2 = decay2

    def forward(self, *x):
        i = 0
        x = [xi.clone().detach() for xi in x]
        for xi, coni in zip(x, self.connection):
            i += coni(xi)
        with torch.no_grad():
            s = self.node(i)
            traceout = self.cal_traceout(s)
            i.data += traceout - i.data
        dw1 = torch.autograd.grad(
            outputs=i,
            inputs=[c.weight for c in self.connection],
            retain_graph=True,
            grad_outputs=i,
        )
        with torch.no_grad():
            i.data += s - i.data
            tracein = self.cal_tracein(x)
            for xi, ti in zip(x, tracein):
                xi.data += ti - xi.data
        dw2 = torch.autograd.grad(
            outputs=i,
            inputs=[c.weight for c in self.connection],
            grad_outputs=i,
        )
        return s, dw2, dw1

    def cal_tracein(self, x):
        for i in range(len(x)):
            if self.tracein[i] is None:
                self.tracein[i] = Parameter(
                    x[i].clone().detach(), requires_grad=False
                )
            else:
                self.tracein[i] *= self.decay
                self.tracein[i] += x[i].detach()
        return self.tracein

    def cal_traceout(self, x):
        if self.traceout is None:
            self.traceout = Parameter(
                torch.zeros_like(x), requires_grad=False
            )
        else:
            self.traceout *= self.decay2
        trace = self.traceout.clone().detach()
        self.traceout += x
        return trace

    def reset(self):
        self.traceout = [None for _ in self.connection]
        self.tracein = None


class Hebb(nn.Module):
    def __init__(self, learning_rate: float = 0.01):
        super().__init__()
        self.lr = learning_rate

    def forward(
        self, pre_spikes: torch.Tensor, post_spikes: torch.Tensor, weight: torch.Tensor
    ) -> torch.Tensor:
        delta_w = self.lr * torch.outer(post_spikes.flatten(), pre_spikes.flatten())
        return weight + delta_w.reshape(weight.shape)


class BCM(nn.Module):
    def __init__(self, learning_rate: float = 0.01, tau_theta: float = 10.0):
        super().__init__()
        self.lr = learning_rate
        self.tau_theta = tau_theta
        self.theta = 0.0

    def forward(
        self, pre_spikes: torch.Tensor, post_spikes: torch.Tensor, weight: torch.Tensor
    ) -> torch.Tensor:
        post_rate = post_spikes.mean().item()
        self.theta += (post_rate - self.theta) / self.tau_theta
        delta_w = self.lr * post_spikes * (post_spikes - self.theta) @ pre_spikes.t()
        return weight + delta_w.reshape(weight.shape)
