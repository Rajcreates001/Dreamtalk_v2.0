import torch
import torch.nn as nn
import torch.nn.functional as F
import torchvision
import cv2
import numpy as np
from .resnet import Resnet18

# CelebAMask-HQ class order, which is what 79999_iter.pth was trained on.
#
# The previous list was a different 19-label ordering: it omitted the
# eyeglasses and earring classes and put hair at 12 instead of 17. The
# network was fine; the names on top of it were not. Segmenting the real
# source portrait made that unmistakable — it reported "right_shoe 40.7%"
# for the man's suit and "bag 3.9%" for his hair, because index 16 is cloth
# and 17 is hair.
FACE_LABELS = [
    "background", "skin", "l_brow", "r_brow", "l_eye",
    "r_eye", "eye_g", "l_ear", "r_ear", "ear_r",
    "nose", "mouth", "u_lip", "l_lip", "neck",
    "neck_l", "cloth", "hair", "hat",
]

SKIN_LABELS = {1}

# Everything MuseTalk regenerates below the eyes: skin, nose, the mouth
# interior and both lips.
#
# This was {1, 8, 9, 10, 11}, chosen against the wrong label list. Under the
# real ordering that set is skin + r_ear + earring + nose + mouth — it pulled
# in the ear and the earring while EXCLUDING both lips (12, 13). The blend
# mask for a talking mouth was leaving the lips out of the mouth region.
JAW_RELATED_LABELS = {1, 10, 11, 12, 13}

# The mouth interior and both lips. This is what the network is for;
# the rest of the lower face is already right in the photograph.
MOUTH_LABELS = {11, 12, 13}

class ConvBNReLU(nn.Module):
    def __init__(self, in_chan, out_chan, ks=3, stride=1, padding=1):
        super(ConvBNReLU, self).__init__()
        self.conv = nn.Conv2d(in_chan, out_chan, kernel_size=ks, stride=stride,
                              padding=padding, bias=False)
        self.bn = nn.BatchNorm2d(out_chan)

    def forward(self, x):
        return F.relu(self.bn(self.conv(x)))


class BiSeNetOutput(nn.Module):
    def __init__(self, in_chan, mid_chan, n_classes):
        super(BiSeNetOutput, self).__init__()
        self.conv = ConvBNReLU(in_chan, mid_chan, ks=3, stride=1, padding=1)
        self.conv_out = nn.Conv2d(mid_chan, n_classes, kernel_size=1, bias=False)

    def forward(self, x):
        return self.conv_out(self.conv(x))


class AttentionRefinementModule(nn.Module):
    def __init__(self, in_chan, out_chan):
        super(AttentionRefinementModule, self).__init__()
        self.conv = ConvBNReLU(in_chan, out_chan, ks=3, stride=1, padding=1)
        self.conv_atten = nn.Conv2d(out_chan, out_chan, kernel_size=1, bias=False)
        self.bn_atten = nn.BatchNorm2d(out_chan)
        self.sigmoid_atten = nn.Sigmoid()

    def forward(self, x):
        feat = self.conv(x)
        atten = F.avg_pool2d(feat, feat.size()[2:])
        atten = self.sigmoid_atten(self.bn_atten(self.conv_atten(atten)))
        return torch.mul(feat, atten)


class ContextPath(nn.Module):
    """ResNet-18 trunk plus attention refinement at 1/16 and 1/32."""

    def __init__(self):
        super(ContextPath, self).__init__()
        self.resnet = Resnet18()
        self.arm16 = AttentionRefinementModule(256, 128)
        self.arm32 = AttentionRefinementModule(512, 128)
        self.conv_head32 = ConvBNReLU(128, 128, ks=3, stride=1, padding=1)
        self.conv_head16 = ConvBNReLU(128, 128, ks=3, stride=1, padding=1)
        self.conv_avg = ConvBNReLU(512, 128, ks=1, stride=1, padding=0)

    def forward(self, x):
        feat8, feat16, feat32 = self.resnet(x)
        h8, w8 = feat8.size()[2:]
        h16, w16 = feat16.size()[2:]
        h32, w32 = feat32.size()[2:]

        avg = F.avg_pool2d(feat32, feat32.size()[2:])
        avg = self.conv_avg(avg)
        avg_up = F.interpolate(avg, (h32, w32), mode='nearest')

        feat32_arm = self.arm32(feat32) + avg_up
        feat32_up = self.conv_head32(
            F.interpolate(feat32_arm, (h16, w16), mode='nearest'))

        feat16_arm = self.arm16(feat16) + feat32_up
        feat16_up = self.conv_head16(
            F.interpolate(feat16_arm, (h8, w8), mode='nearest'))

        # feat8 doubles as the spatial path: this architecture has no separate
        # SpatialPath branch, which is why the checkpoint carries no
        # spatial_path.* keys at all.
        return feat8, feat16_up, feat32_up


class FeatureFusionModule(nn.Module):
    def __init__(self, in_chan, out_chan):
        super(FeatureFusionModule, self).__init__()
        self.convblk = ConvBNReLU(in_chan, out_chan, ks=1, stride=1, padding=0)
        self.conv1 = nn.Conv2d(out_chan, out_chan // 4, kernel_size=1, bias=False)
        self.conv2 = nn.Conv2d(out_chan // 4, out_chan, kernel_size=1, bias=False)
        self.relu = nn.ReLU(inplace=True)
        self.sigmoid = nn.Sigmoid()

    def forward(self, fsp, fcp):
        feat = self.convblk(torch.cat([fsp, fcp], dim=1))
        atten = F.avg_pool2d(feat, feat.size()[2:])
        atten = self.sigmoid(self.conv2(self.relu(self.conv1(atten))))
        return feat + torch.mul(feat, atten)


class BiSeNet(nn.Module):
    """Face-parsing BiSeNet matching weights/retinaface/79999_iter.pth.

    Module names are load-bearing: cp / ffm / conv_out / conv_out16 /
    conv_out32 are what the checkpoint's 191 keys are named after, so
    renaming any of them silently reverts this to the geometric-ellipse
    fallback. load_state_dict is called with strict=True by FaceParsing for
    exactly that reason.
    """

    def __init__(self, n_classes=19, left_cheek_width=90, right_cheek_width=90):
        super(BiSeNet, self).__init__()
        self.n_classes = n_classes
        self.left_cheek_width = left_cheek_width
        self.right_cheek_width = right_cheek_width

        self.cp = ContextPath()
        self.ffm = FeatureFusionModule(256, 256)
        self.conv_out = BiSeNetOutput(256, 256, n_classes)
        self.conv_out16 = BiSeNetOutput(128, 64, n_classes)
        self.conv_out32 = BiSeNetOutput(128, 64, n_classes)

    def forward(self, x):
        h, w = x.size()[2:]
        feat_res8, feat_cp8, feat_cp16 = self.cp(x)
        feat_fuse = self.ffm(feat_res8, feat_cp8)
        feat_out = self.conv_out(feat_fuse)
        # Only the main head is used at inference; conv_out16/32 exist because
        # the checkpoint carries their weights (deep supervision during
        # training) and strict loading requires them to be present.
        return F.interpolate(feat_out, (h, w), mode='bilinear', align_corners=True)


def _cone_kernel(size: int) -> np.ndarray:
    """Radial falloff weight: 1.0 at the centre, 0 at the rim.

    This is a per-pixel ALPHA WEIGHT, not a convolution kernel, and the
    difference is the whole bug. It used to return kernel / kernel.sum(),
    which is right for convolution and catastrophic here: for the ~373px
    cone a real crop produces, sum-normalising puts the peak at about
    2.7e-5, so _get_jaw_mask's `mask * cone` turned 255 into 0.007 and the
    uint8 cast floored every pixel to zero.

    The result was an entirely empty jaw mask, so MuseTalk pasted nothing and
    rendered a video in which even the mouth never moved. It stayed hidden
    because the face parser had never successfully loaded — the geometric
    fallback ran instead, and this line was dead code until the parser was
    repaired.

    kernel already peaks at 1.0 by construction, so normalise by max.
    """
    kernel = np.zeros((size, size), dtype=np.float32)
    center = size // 2
    for i in range(size):
        for j in range(size):
            dist = np.sqrt((i - center) ** 2 + (j - center) ** 2)
            kernel[i, j] = max(0, 1.0 - dist / center)
    peak = float(kernel.max())
    return kernel / peak if peak > 0 else kernel


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
        """Where MuseTalk's output is allowed to replace the photograph.

        This used to be every skin pixel, weighted by a cone peaking near the
        bottom of the crop - so the region it replaced hardest was the chin,
        and the whole lower face came from the network. On a subject with a
        beard that is the worst possible choice. MuseTalk smooths heavy facial
        hair away, and rendered frames came back with the beard erased into a
        pale blotchy chin and a visibly reshaped jawline, against a source
        photograph with a full dark beard. Looking at one frame showed it
        immediately; four renders of mouth metrics had not, because none of
        them looked outside the mouth.

        The network only needs the mouth. Everything else in the lower face is
        already correct in the photograph and moves very little on a frontal
        talking head, so it is kept. The mask is now the mouth and lips grown
        by a margin proportional to the mouth's own width, clipped to face
        skin so it cannot bleed into beard-free background or hair, and
        feathered.

        If the parser finds no mouth - a closed, dark mouth on a low-contrast
        frame - this falls back to the previous behaviour rather than
        returning an empty mask, because no mask at all means no lip-sync.
        """
        h, w = parsing.shape
        mouth = np.isin(parsing, list(MOUTH_LABELS))
        if not mouth.any():
            return self._get_jaw_mask_legacy(parsing, image)

        ys, xs = np.nonzero(mouth)
        mouth_w = max(1, int(xs.max() - xs.min()))
        grow = max(3, int(mouth_w * 0.55))
        if grow % 2 == 0:
            grow += 1
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (grow, grow))
        grown = cv2.dilate(mouth.astype(np.uint8), kernel, iterations=1)

        # Stay on the face. Without this the dilation walks onto the beard
        # boundary and the background either side of the chin.
        face = np.isin(parsing, list(SKIN_LABELS | MOUTH_LABELS | {10}))
        mask = (grown.astype(bool) & face).astype(np.float32) * 255.0

        # Feather, scaled to the mouth rather than the crop, so the seam falls
        # inside skin that barely moves.
        blur = max(3.0, mouth_w * 0.18)
        mask = cv2.GaussianBlur(mask, (0, 0), sigmaX=blur)
        return Image.fromarray(np.clip(mask, 0, 255).astype(np.uint8))

    def _get_jaw_mask_legacy(self, parsing: np.ndarray, image):
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
