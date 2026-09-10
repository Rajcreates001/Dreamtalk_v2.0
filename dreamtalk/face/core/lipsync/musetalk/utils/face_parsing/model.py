import torch
import torch.nn as nn
import torch.nn.functional as F
import torchvision
import cv2
import numpy as np
from .resnet import Resnet18

FACE_LABELS = [
    "background", "skin", "left_brow", "right_brow", "left_eye",
    "right_eye", "left_ear", "right_ear", "nose", "upper_lip",
    "lower_lip", "inner_mouth", "hair", "neck", "clothes",
    "left_shoe", "right_shoe", "bag", "scarf",
]

SKIN_LABELS = {1}

JAW_RELATED_LABELS = {1, 8, 9, 10, 11}

class ConvBNReLU(nn.Module):
    def __init__(self, in_chan, out_chan, ks=3, stride=1, padding=1):
        super(ConvBNReLU, self).__init__()
        self.conv = nn.Conv2d(in_chan, out_chan, kernel_size=ks, stride=stride, padding=padding, bias=False)
        self.bn = nn.BatchNorm2d(out_chan)
        self.relu = nn.ReLU(inplace=True)

    def forward(self, x):
        x = self.conv(x)
        x = self.bn(x)
        x = self.relu(x)
        return x


class SpatialPath(nn.Module):
    def __init__(self):
        super(SpatialPath, self).__init__()
        self.conv1 = ConvBNReLU(3, 64, ks=7, stride=2, padding=3)
        self.conv2 = ConvBNReLU(64, 64, ks=3, stride=2, padding=1)
        self.conv3 = ConvBNReLU(64, 64, ks=3, stride=2, padding=1)
        self.conv4 = ConvBNReLU(64, 64, ks=3, stride=1, padding=1)

    def forward(self, x):
        x = self.conv1(x)
        x = self.conv2(x)
        x = self.conv3(x)
        x = self.conv4(x)
        return x


class AttentionRefinementModule(nn.Module):
    def __init__(self, in_chan, out_chan):
        super(AttentionRefinementModule, self).__init__()
        self.conv = ConvBNReLU(in_chan, out_chan, ks=3, stride=1, padding=1)
        self.conv_atten = nn.Conv2d(out_chan, out_chan, kernel_size=1, bias=False)
        self.bn_atten = nn.BatchNorm2d(out_chan)
        self.sigmoid = nn.Sigmoid()

    def forward(self, x):
        x = self.conv(x)
        feat = x
        atten = F.avg_pool2d(feat, feat.size()[2:])
        atten = self.conv_atten(atten)
        atten = self.bn_atten(atten)
        atten = self.sigmoid(atten)
        out = torch.mul(feat, atten)
        return out


class ContextPath(nn.Module):
    def __init__(self):
        super(ContextPath, self).__init__()
        self.resnet = Resnet18()
        self.arm16 = AttentionRefinementModule(256, 128)
        self.arm32 = AttentionRefinementModule(512, 128)
        self.conv_avg = ConvBNReLU(512, 128, ks=1, stride=1, padding=0)

    def forward(self, x):
        x = self.resnet.conv1(x)
        x = self.resnet.bn1(x)
        x = self.resnet.relu(x)
        x = self.resnet.maxpool(x)
        x = self.resnet.layer1(x)
        f8 = x
        x = self.resnet.layer2(x)
        f16 = x
        x = self.resnet.layer3(x)
        f32 = x
        x = self.resnet.layer4(x)
        f64 = x

        f16_arm = self.arm16(f16)
        f32_arm = self.arm32(f32)
        f64_avg = F.avg_pool2d(f64, f64.size()[2:])
        f64_avg = self.conv_avg(f64_avg)
        f64_avg_up = F.interpolate(f64_avg, size=f32_arm.size()[2:], mode='nearest')
        f32_up = F.interpolate(f32_arm, size=f16_arm.size()[2:], mode='nearest')
        f16_up = F.interpolate(f16_arm, size=f8.size()[2:], mode='nearest')
        return f8, f16_up, f32_up, f64_avg_up


class FeatureFusionModule(nn.Module):
    def __init__(self, in_chan, out_chan):
        super(FeatureFusionModule, self).__init__()
        self.convblk = ConvBNReLU(in_chan, out_chan, ks=3, stride=1, padding=1)
        self.conv1 = nn.Conv2d(out_chan, out_chan // 4, kernel_size=1, bias=False)
        self.conv2 = nn.Conv2d(out_chan // 4, out_chan, kernel_size=1, bias=False)
        self.relu = nn.ReLU(inplace=True)
        self.sigmoid = nn.Sigmoid()

    def forward(self, fsp, fcp):
        fcat = torch.cat([fsp, fcp], dim=1)
        feat = self.convblk(fcat)
        atten = F.avg_pool2d(feat, feat.size()[2:])
        atten = self.conv1(atten)
        atten = self.relu(atten)
        atten = self.conv2(atten)
        atten = self.sigmoid(atten)
        feat_atten = torch.mul(feat, atten)
        feat_out = feat_atten + feat
        return feat_out


class BiSeNet(nn.Module):
    def __init__(self, n_classes=19, left_cheek_width=90, right_cheek_width=90):
        super(BiSeNet, self).__init__()
        self.n_classes = n_classes
        self.left_cheek_width = left_cheek_width
        self.right_cheek_width = right_cheek_width

        self.spatial_path = SpatialPath()
        self.context_path = ContextPath()
        self.ffm = FeatureFusionModule(64 + 128, 256)
        self.conv_out = nn.Sequential(
            nn.Conv2d(256, 256, kernel_size=1, bias=False),
            nn.BatchNorm2d(256),
            nn.ReLU(inplace=True),
            nn.Conv2d(256, n_classes, kernel_size=1),
        )

    def forward(self, x):
        fsp = self.spatial_path(x)
        f8, f16_up, f32_up, f64_avg_up = self.context_path(x)
        fcp = f16_up
        fcat = torch.cat([fsp, fcp], dim=1)
        fcat = F.interpolate(fcat, scale_factor=8, mode='bilinear', align_corners=True)
        feat = self.ffm(fsp, fcp)
        feat = F.interpolate(feat, scale_factor=8, mode='bilinear', align_corners=True)
        out = self.conv_out(feat)
        out = F.interpolate(out, scale_factor=4, mode='bilinear', align_corners=True)
        return out


def _cone_kernel(size: int) -> np.ndarray:
    kernel = np.zeros((size, size), dtype=np.float32)
    center = size // 2
    for i in range(size):
        for j in range(size):
            dist = np.sqrt((i - center) ** 2 + (j - center) ** 2)
            kernel[i, j] = max(0, 1.0 - dist / center)
    return kernel / kernel.sum()


def _cheek_erosion(mask: np.ndarray, erode_kernel_size: int = 7) -> np.ndarray:
    kernel = np.ones((erode_kernel_size, erode_kernel_size), dtype=np.uint8)
    return cv2.erode(mask.astype(np.uint8), kernel, iterations=1)


class FaceParsing():
    def __init__(self, model_path=None, left_cheek_width=90, right_cheek_width=90):
        if model_path is None:
            import os
            from pathlib import Path
            # From face_parsing/model.py: utils/ → musetalk/ → lipsync/ → core/ → face/ → dreamtalk/ → root (8 levels)
            _root = Path(__file__).resolve().parent.parent.parent.parent.parent.parent.parent
            model_path = str(_root / "weights/retinaface/79999_iter.pth")
        self.n_classes = 19
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.net = BiSeNet(n_classes=self.n_classes, left_cheek_width=left_cheek_width, right_cheek_width=right_cheek_width)
        self.net.to(self.device)
        if torch.cuda.is_available():
            state_dict = torch.load(model_path)
        else:
            state_dict = torch.load(model_path, map_location=torch.device('cpu'))
        self.net.load_state_dict(state_dict)
        self.net.eval()
        self._cone_cache: dict = {}

    def __call__(self, image, mode="raw"):
        with torch.no_grad():
            image_copy = np.array(image).copy()
            tensor = torchvision.transforms.ToTensor()(image_copy).unsqueeze(0).to(self.device)
            tensor = (tensor - 0.5) / 0.5
            out = self.net(tensor)
            parsing = out.squeeze(0).argmax(0).cpu().numpy()

        if mode == "raw":
            return self._get_skin_mask(parsing)

        elif mode == "jaw":
            return self._get_jaw_mask(parsing, image)

        elif mode == "cheek":
            return self._get_cheek_mask(parsing, image)

        elif mode == "all":
            return parsing

        return self._get_skin_mask(parsing)

    def _get_skin_mask(self, parsing: np.ndarray):
        mask = np.zeros_like(parsing, dtype=np.uint8)
        for label in SKIN_LABELS:
            mask[parsing == label] = 255
        return Image.fromarray(mask)

    def _get_jaw_mask(self, parsing: np.ndarray, image):
        h, w = parsing.shape
        mask = np.zeros((h, w), dtype=np.uint8)
        for label in JAW_RELATED_LABELS:
            mask[parsing == label] = 255

        cone_h = int(h * 0.75)
        cone_w = int(w * 0.9)
        cone_size = max(cone_h, cone_w)
        if cone_size % 2 == 0:
            cone_size += 1

        if cone_size not in self._cone_cache:
            self._cone_cache[cone_size] = _cone_kernel(cone_size)
        cone_kernel = self._cone_cache[cone_size]

        cone_mask = np.zeros((h, w), dtype=np.float32)
        y_start = max(0, h - cone_h)
        y_end = min(h, y_start + cone_size)
        x_start = max(0, (w - cone_w) // 2)
        x_end = min(w, x_start + cone_size)
        ky_start = max(0, cone_size - (y_end - y_start))
        kx_start = max(0, cone_size - (x_end - x_start))
        cone_mask[y_start:y_end, x_start:x_end] = \
            cone_kernel[ky_start:ky_start + (y_end - y_start), kx_start:kx_start + (x_end - x_start)]

        mask = (mask.astype(np.float32) * cone_mask).astype(np.uint8)
        return Image.fromarray(mask)

    def _get_cheek_mask(self, parsing: np.ndarray, image):
        h, w = parsing.shape
        skin_mask = np.zeros((h, w), dtype=np.uint8)
        for label in SKIN_LABELS:
            skin_mask[parsing == label] = 255

        neck_mask = np.zeros((h, w), dtype=np.uint8)
        neck_mask[parsing == 13] = 255

        left_cheek = self.net.left_cheek_width
        right_cheek = self.net.right_cheek_width

        eroded_skin = _cheek_erosion(skin_mask, erode_kernel_size=7)
        inflated_neck = cv2.dilate(neck_mask, np.ones((3, 3), dtype=np.uint8), iterations=2)
        cheek_mask = eroded_skin.copy()
        cheek_mask[inflated_neck > 0] = 0

        return Image.fromarray(cheek_mask)


from PIL import Image
