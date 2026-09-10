"""PFLD — Principled Facial Landmark Detection.

A lightweight, high-precision face alignment network.
Architecture: MobileNet-like backbone + auxiliary attribute prediction branch.
Outputs 106 2D facial landmarks.
https://arxiv.org/abs/1902.10859
"""

import torch
import torch.nn as nn
import torch.nn.functional as F


class _InvertedResidual(nn.Module):
    """MobileNetV2 inverted residual block with optional stride."""

    def __init__(self, in_ch, out_ch, stride, expand_ratio):
        super().__init__()
        hidden_dim = round(in_ch * expand_ratio)
        self.use_res_connect = stride == 1 and in_ch == out_ch

        layers = []
        if expand_ratio != 1:
            layers.append(nn.Conv2d(in_ch, hidden_dim, 1, bias=False))
            layers.append(nn.BatchNorm2d(hidden_dim))
            layers.append(nn.ReLU6(inplace=True))

        layers.extend([
            nn.Conv2d(hidden_dim, hidden_dim, 3, stride, 1, groups=hidden_dim, bias=False),
            nn.BatchNorm2d(hidden_dim),
            nn.ReLU6(inplace=True),
            nn.Conv2d(hidden_dim, out_ch, 1, bias=False),
            nn.BatchNorm2d(out_ch),
        ])
        self.conv = nn.Sequential(*layers)

    def forward(self, x):
        if self.use_res_connect:
            return x + self.conv(x)
        return self.conv(x)


class _AuxiliaryNet(nn.Module):
    """Auxiliary attribute prediction network for PFLD training stability."""

    def __init__(self):
        super().__init__()
        self.conv1 = nn.Conv2d(128, 128, 3, stride=2, padding=1)
        self.conv2 = nn.Conv2d(128, 128, 3, stride=1, padding=1)
        self.conv3 = nn.Conv2d(128, 32, 3, stride=2, padding=1)
        self.conv4 = nn.Conv2d(32, 128, 7, stride=1, padding=0)
        self.fc = nn.Linear(128, 3)  # pitch, yaw, roll

    def forward(self, x):
        x = F.relu(self.conv1(x))
        x = F.relu(self.conv2(x))
        x = F.relu(self.conv3(x))
        x = F.relu(self.conv4(x))
        x = x.view(x.size(0), -1)
        return self.fc(x)


class PFLDModel(nn.Module):
    """PFLD face landmark detector.

    Input:  1×112×96 grayscale image
    Output: 106×2 facial landmarks (normalized to [0,1])
    """

    def __init__(self, num_landmarks: int = 106):
        super().__init__()
        self.num_landmarks = num_landmarks

        # Stem
        self.conv1 = nn.Conv2d(1, 64, 3, stride=2, padding=1)
        self.bn1 = nn.BatchNorm2d(64)
        self.relu1 = nn.ReLU(inplace=True)

        # Backbone (MobileNetV2-style inverted residuals)
        self.block1 = _InvertedResidual(64, 64, 2, 2)   # 56×48
        self.block2 = _InvertedResidual(64, 64, 1, 2)
        self.block3 = _InvertedResidual(64, 64, 1, 2)
        self.block4 = _InvertedResidual(64, 64, 1, 2)

        self.conv2 = nn.Conv2d(64, 128, 3, stride=2, padding=1)
        self.bn2 = nn.BatchNorm2d(128)
        self.relu2 = nn.ReLU(inplace=True)

        self.block5 = _InvertedResidual(128, 128, 1, 4)  # 28×24
        self.block6 = _InvertedResidual(128, 128, 1, 4)
        self.block7 = _InvertedResidual(128, 128, 1, 4)
        self.block8 = _InvertedResidual(128, 128, 1, 4)

        # Auxiliary network
        self.aux_net = _AuxiliaryNet()

        # Landmark prediction head
        self.conv3 = nn.Conv2d(128, 32, 3, stride=2, padding=1)  # 14×12
        self.bn3 = nn.BatchNorm2d(32)
        self.relu3 = nn.ReLU(inplace=True)

        self.conv4 = nn.Conv2d(32, 32, 3, stride=1, padding=1)
        self.bn4 = nn.BatchNorm2d(32)
        self.relu4 = nn.ReLU(inplace=True)

        self.conv5 = nn.Conv2d(32, 32, 3, stride=2, padding=1)   # 7×6
        self.bn5 = nn.BatchNorm2d(32)
        self.relu5 = nn.ReLU(inplace=True)

        self.conv6 = nn.Conv2d(32, 32, 3, stride=1, padding=0)   # 5×4
        self.bn6 = nn.BatchNorm2d(32)
        self.relu6 = nn.ReLU(inplace=True)

        # Fully connected
        self.fc1 = nn.Linear(5 * 4 * 32, 256)
        self.fc2 = nn.Linear(256, num_landmarks * 2)

        # Initialize weights
        self._init_weights()

    def _init_weights(self):
        for m in self.modules():
            if isinstance(m, nn.Conv2d):
                nn.init.kaiming_normal_(m.weight, mode='fan_out', nonlinearity='relu')
                if m.bias is not None:
                    nn.init.zeros_(m.bias)
            elif isinstance(m, nn.BatchNorm2d):
                nn.init.ones_(m.weight)
                nn.init.zeros_(m.bias)
            elif isinstance(m, nn.Linear):
                nn.init.normal_(m.weight, 0, 0.01)
                if m.bias is not None:
                    nn.init.zeros_(m.bias)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Forward pass.

        Args:
            x: (batch, 1, 112, 96) normalized face image

        Returns:
            landmarks: (batch, num_landmarks, 2) normalized to [0,1]
        """
        # Stem
        x = self.relu1(self.bn1(self.conv1(x)))

        # MobileNet blocks
        x = self.block1(x)
        x = self.block2(x)
        x = self.block3(x)
        x = self.block4(x)

        x = self.relu2(self.bn2(self.conv2(x)))

        x = self.block5(x)
        x = self.block6(x)
        x = self.block7(x)
        x = self.block8(x)

        # Auxiliary (for training stability; not used at inference)
        aux = self.aux_net(x)

        # Landmark head
        x = self.relu3(self.bn3(self.conv3(x)))
        x = self.relu4(self.bn4(self.conv4(x)))
        x = self.relu5(self.bn5(self.conv5(x)))
        x = self.relu6(self.bn6(self.conv6(x)))

        x = x.view(x.size(0), -1)
        x = F.relu(self.fc1(x))
        landmarks = self.fc2(x)

        # Reshape to (batch, num_landmarks, 2) and normalize to [0,1]
        landmarks = landmarks.view(-1, self.num_landmarks, 2)
        landmarks = torch.sigmoid(landmarks)

        return landmarks

    @torch.no_grad()
    def predict(self, image_tensor: torch.Tensor) -> torch.Tensor:
        """Inference wrapper with no grad.

        Args:
            image_tensor: (1, 1, 112, 96) or (batch, 1, 112, 96)

        Returns:
            landmarks: (batch, num_landmarks, 2)
        """
        self.eval()
        if image_tensor.dim() == 3:
            image_tensor = image_tensor.unsqueeze(0)
        return self.forward(image_tensor)


def create_pfld_model(weight_path: str = None, device: str = "cpu", num_landmarks: int = 106) -> PFLDModel:
    """Create PFLD model and optionally load weights.

    Args:
        weight_path: Path to .pth weight file
        device: torch device
        num_landmarks: Number of facial landmarks (default 106)

    Returns:
        Loaded PFLDModel in eval mode
    """
    model = PFLDModel(num_landmarks=num_landmarks)
    if weight_path:
        state = torch.load(weight_path, map_location=device, weights_only=True)
        # Handle different state dict formats
        if "state_dict" in state:
            model.load_state_dict(state["state_dict"])
        elif "model_state" in state:
            model.load_state_dict(state["model_state"])
        else:
            model.load_state_dict(state)
    model = model.to(device)
    model.eval()
    return model
