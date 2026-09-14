# Dreamtalk - Face Engine
"""ResNet-18 backbone for the BiSeNet face parser.

This must be the torchvision-style BasicBlock ResNet, because the shipped
checkpoint (weights/retinaface/79999_iter.pth) was trained against it: its
keys are cp.resnet.layer1.0.conv1.weight, .bn1.*, .downsample.0/.1, and so on.

The previous implementation here was a flat nn.Sequential stack whose keys
were layer1.0.weight / layer1.1.* — 54 parameters against the checkpoint's
120. load_state_dict therefore failed on every start with a wall of missing
and unexpected keys, FaceParsing was set to None, and MuseTalk silently fell
back to a geometric ellipse instead of real face segmentation. The fallback
worked, which is precisely why the mismatch went unnoticed.
"""

import torch
import torch.nn as nn
import torch.nn.functional as F


def conv3x3(in_planes, out_planes, stride=1):
    return nn.Conv2d(in_planes, out_planes, kernel_size=3, stride=stride,
                     padding=1, bias=False)


class BasicBlock(nn.Module):
    """Standard ResNet basic block: conv-bn-relu-conv-bn + identity."""

    def __init__(self, in_chan, out_chan, stride=1):
        super(BasicBlock, self).__init__()
        self.conv1 = conv3x3(in_chan, out_chan, stride)
        self.bn1 = nn.BatchNorm2d(out_chan)
        self.conv2 = conv3x3(out_chan, out_chan)
        self.bn2 = nn.BatchNorm2d(out_chan)
        self.relu = nn.ReLU(inplace=True)
        self.downsample = None
        if in_chan != out_chan or stride != 1:
            self.downsample = nn.Sequential(
                nn.Conv2d(in_chan, out_chan, kernel_size=1, stride=stride, bias=False),
                nn.BatchNorm2d(out_chan),
            )

    def forward(self, x):
        residual = self.conv1(x)
        residual = F.relu(self.bn1(residual))
        residual = self.conv2(residual)
        residual = self.bn2(residual)

        shortcut = x if self.downsample is None else self.downsample(x)
        return self.relu(shortcut + residual)


def create_layer_basic(in_chan, out_chan, bnum, stride=1):
    layers = [BasicBlock(in_chan, out_chan, stride=stride)]
    layers += [BasicBlock(out_chan, out_chan, stride=1) for _ in range(bnum - 1)]
    return nn.Sequential(*layers)


class Resnet18(nn.Module):
    """ResNet-18 trunk returning the three scales BiSeNet's ContextPath needs."""

    def __init__(self):
        super(Resnet18, self).__init__()
        self.conv1 = nn.Conv2d(3, 64, kernel_size=7, stride=2, padding=3, bias=False)
        self.bn1 = nn.BatchNorm2d(64)
        self.maxpool = nn.MaxPool2d(kernel_size=3, stride=2, padding=1)
        self.layer1 = create_layer_basic(64, 64, bnum=2, stride=1)
        self.layer2 = create_layer_basic(64, 128, bnum=2, stride=2)
        self.layer3 = create_layer_basic(128, 256, bnum=2, stride=2)
        self.layer4 = create_layer_basic(256, 512, bnum=2, stride=2)

    def forward(self, x):
        x = self.conv1(x)
        x = F.relu(self.bn1(x))
        x = self.maxpool(x)

        x = self.layer1(x)
        feat8 = self.layer2(x)      # 1/8   scale, 128 channels
        feat16 = self.layer3(feat8)  # 1/16  scale, 256 channels
        feat32 = self.layer4(feat16)  # 1/32 scale, 512 channels
        return feat8, feat16, feat32
