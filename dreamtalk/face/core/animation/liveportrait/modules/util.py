# Dreamtalk - Face Engine
# Extracted from LivePortrait
import torch
from torch import nn
import torch.nn.functional as F
import numpy as np


def filter_state_dict(state_dict, remove_name='head'):
    new_state_dict = {}
    for key in state_dict:
        if remove_name in key:
            continue
        new_state_dict[key] = state_dict[key]
    return new_state_dict


def make_coordinate_grid(spatial_size, ref=None):
    d, h, w = spatial_size
    x = torch.arange(w).to(ref)
    y = torch.arange(h).to(ref)
    z = torch.arange(d).to(ref)

    x = (2 * (x / (w - 1)) - 1)
    y = (2 * (y / (h - 1)) - 1)
    z = (2 * (z / (d - 1)) - 1)

    yy = y.view(1, -1, 1).repeat(d, 1, w)
    xx = x.view(1, 1, -1).repeat(d, h, 1)
    zz = z.view(-1, 1, 1).repeat(1, h, w)

    grid = torch.stack([xx, yy, zz], dim=-1)
    return grid


def kp2gaussian(kp, spatial_size, kp_variance):
    mean = kp
    d, h, w = spatial_size
    coordinate_grid = make_coordinate_grid(spatial_size, ref=kp)
    number_of_leading_dimensions = kp.shape[:-1]
    shape = (1,) + (1,) + (d, h, w) + (3,)
    coordinate_grid = coordinate_grid.view(*shape)
    repeats = number_of_leading_dimensions + (1, 1, 1, 1)
    coordinate_grid = coordinate_grid.repeat(*repeats)

    mean = mean.view(mean.shape[:2] + (1, 1, 1, mean.shape[-1]))
    mean = mean.repeat(1, 1, d, h, w, 1)

    gaussian = - (0.5) * (coordinate_grid - mean).pow(2).sum(-1) / kp_variance
    return gaussian


class DownBlock2d(nn.Module):
    def __init__(self, in_features, out_features, kernel_size=3, padding=1, groups=1):
        super(DownBlock2d, self).__init__()
        self.conv = nn.Conv2d(in_channels=in_features, out_channels=out_features, kernel_size=kernel_size, padding=padding, groups=groups)
        self.norm = nn.BatchNorm2d(out_features, affine=True)
        self.pool = nn.AvgPool2d(kernel_size=(2, 2))

    def forward(self, x):
        out = self.conv(x)
        out = self.norm(out)
        out = F.relu(out)
        out = self.pool(out)
        return out


class SameBlock2d(nn.Module):
    def __init__(self, in_features, out_features, kernel_size=3, padding=1, lrelu=False, groups=1):
        super(SameBlock2d, self).__init__()
        self.conv = nn.Conv2d(in_channels=in_features, out_channels=out_features, kernel_size=kernel_size, padding=padding, groups=groups)
        self.norm = nn.BatchNorm2d(out_features, affine=True)
        if lrelu:
            self.ac = nn.LeakyReLU()
        else:
            self.ac = nn.ReLU()

    def forward(self, x):
        out = self.conv(x)
        out = self.norm(out)
        out = self.ac(out)
        return out


class ResBlock3d(nn.Module):
    def __init__(self, in_features, kernel_size, padding):
        super(ResBlock3d, self).__init__()
        self.conv1 = nn.Conv3d(in_channels=in_features, out_channels=in_features, kernel_size=kernel_size, padding=padding)
        self.conv2 = nn.Conv3d(in_channels=in_features, out_channels=in_features, kernel_size=kernel_size, padding=padding)
        self.norm1 = nn.BatchNorm3d(in_features, affine=True)
        self.norm2 = nn.BatchNorm3d(in_features, affine=True)

    def forward(self, x):
        out = self.norm1(x)
        out = F.relu(out)
        out = self.conv1(out)
        out = self.norm2(out)
        out = F.relu(out)
        out = self.conv2(out)
        out += x
        return out


class SPADEResnetBlock(nn.Module):
    def __init__(self, fin, fout, norm_G, label_nc, use_se=False, dilation=1):
        super(SPADEResnetBlock, self).__init__()
        self.learned_shortcut = (fin != fout)
        fmiddle = min(fin, fout)
        self.conv_0 = nn.Conv2d(fin, fmiddle, kernel_size=3, padding=dilation, dilation=dilation)
        self.conv_1 = nn.Conv2d(fmiddle, fout, kernel_size=3, padding=dilation, dilation=dilation)
        if self.learned_shortcut:
            self.conv_s = nn.Conv2d(fin, fout, kernel_size=1, bias=False)

        # Apply spectral norm if requested (checkpoint was trained with spectral norm)
        if 'spectral' in norm_G:
            self.conv_0 = torch.nn.utils.spectral_norm(self.conv_0)
            self.conv_1 = torch.nn.utils.spectral_norm(self.conv_1)
            if self.learned_shortcut:
                self.conv_s = torch.nn.utils.spectral_norm(self.conv_s)

        # norm_G string is used above for spectral norm detection; pass fin/label_nc as ints
        self.norm_0 = SPADE(fin, label_nc)
        self.norm_1 = SPADE(fmiddle, label_nc)
        if self.learned_shortcut:
            self.norm_s = SPADE(fin, label_nc)

    def forward(self, x, seg):
        x_s = self.shortcut(x, seg)
        dx = self.conv_0(self.act(self.norm_0(x, seg)))
        dx = self.conv_1(self.act(self.norm_1(dx, seg)))
        out = x_s + dx
        return out

    def shortcut(self, x, seg):
        if self.learned_shortcut:
            x_s = self.conv_s(self.norm_s(x, seg))
        else:
            x_s = x
        return x_s

    def act(self, x):
        return F.leaky_relu(x, 2e-1)


class SPADE(nn.Module):
    def __init__(self, norm_nc, label_nc, nhidden=128):
        super(SPADE, self).__init__()
        pw = 3
        self.mlp_shared = nn.Sequential(
            nn.Conv2d(label_nc, nhidden, kernel_size=pw, padding=pw // 2),
            nn.ReLU()
        )
        self.mlp_gamma = nn.Conv2d(nhidden, norm_nc, kernel_size=pw, padding=pw // 2)
        self.mlp_beta = nn.Conv2d(nhidden, norm_nc, kernel_size=pw, padding=pw // 2)

    def forward(self, x, seg):
        # Interpolate seg to match x's spatial dimensions (handles upsampling in SpadeDecoder)
        if seg.shape[-2:] != x.shape[-2:]:
            seg = F.interpolate(seg, size=x.shape[-2:], mode='nearest')
        actv = self.mlp_shared(seg)
        gamma = self.mlp_gamma(actv)
        beta = self.mlp_beta(actv)
        out = x * (1 + gamma) + beta
        return out


class DownBlock3d(nn.Module):
    """Downsampling block: Conv3d + BN + ReLU + AvgPool3d(1,2,2)
    Only downsamples H and W, keeping D dimension unchanged for skip connections."""
    def __init__(self, in_features, out_features, kernel_size=3, stride=1, padding=1):
        super(DownBlock3d, self).__init__()
        self.conv = nn.Conv3d(in_features, out_features, kernel_size=kernel_size, stride=stride, padding=padding)
        self.norm = nn.BatchNorm3d(out_features, affine=True)
        self.pool = nn.AvgPool3d(kernel_size=(1, 2, 2))

    def forward(self, x):
        out = self.conv(x)
        out = self.norm(out)
        out = F.relu(out)
        out = self.pool(out)
        return out


class UpBlock3d(nn.Module):
    """Upsampling block: interpolate + Conv3d + BN + ReLU"""
    def __init__(self, in_features, out_features, kernel_size=3, padding=1):
        super(UpBlock3d, self).__init__()
        self.conv = nn.Conv3d(in_channels=in_features, out_channels=out_features, kernel_size=kernel_size, padding=padding)
        self.norm = nn.BatchNorm3d(out_features, affine=True)

    def forward(self, x):
        out = F.interpolate(x, scale_factor=(1, 2, 2))
        out = self.conv(out)
        out = self.norm(out)
        out = F.relu(out)
        return out


class Encoder(nn.Module):
    """
    Hourglass Encoder.
    Checkpoint key structure: encoder.down_blocks.N.conv.*, encoder.down_blocks.N.norm.*
    """
    def __init__(self, block_expansion, in_features, max_features, num_blocks):
        super(Encoder, self).__init__()
        self.down_blocks = nn.ModuleList()

        # Entry block (i=0): k=3, stride=1, no downsampling: in_features -> min(max_features, block_expansion)
        entry_f = min(max_features, block_expansion)
        self.down_blocks.append(DownBlock3d(in_features, entry_f, kernel_size=3, stride=1, padding=1))

        # Down blocks (i=1..num_blocks-1): k=3, AvgPool3d handles (1,2,2) downsampling
        for i in range(1, num_blocks):
            in_f = min(max_features, block_expansion * (2 ** (i - 1)))
            out_f = min(max_features, block_expansion * (2 ** i))
            self.down_blocks.append(DownBlock3d(in_f, out_f, kernel_size=3, stride=1, padding=1))

    def forward(self, x):
        outs = [x]
        for block in self.down_blocks:
            outs.append(block(outs[-1]))
        return outs


class Decoder(nn.Module):
    """
    Hourglass Decoder with skip connections.
    Checkpoint key structure: decoder.up_blocks.*, decoder.conv.*, decoder.norm.*
    """
    def __init__(self, block_expansion, in_features, max_features, num_blocks, enc_dims):
        super(Decoder, self).__init__()
        self.up_blocks = nn.Sequential()

        prev_up_out = None
        for i in range(num_blocks):
            if i == 0:
                in_ch = enc_dims[-1]
            else:
                skip_dims = enc_dims[num_blocks - i]
                in_ch = prev_up_out + skip_dims

            enc_level = num_blocks - i - 1
            up_out_f = min(max_features, block_expansion * (2 ** enc_level)) // 2

            self.up_blocks.add_module(str(i), UpBlock3d(in_ch, up_out_f))
            prev_up_out = up_out_f

        # Final conv+norm after all up blocks and last skip
        out_filters = prev_up_out + in_features
        self.conv = nn.Conv3d(out_filters, out_filters, kernel_size=3, padding=1)
        self.norm = nn.BatchNorm3d(out_filters, affine=True)

    def forward(self, enc_outs):
        out = enc_outs[-1]
        for i, up_block in enumerate(self.up_blocks):
            out = up_block(out)
            if i < len(self.up_blocks) - 1:
                skip_idx = max(1, len(self.up_blocks) - 1 - i)
                out = torch.cat([out, enc_outs[skip_idx]], dim=1)
            else:
                out = torch.cat([out, enc_outs[0]], dim=1)

        out = self.conv(out)
        out = self.norm(out)
        out = F.relu(out)
        return out


class Hourglass(nn.Module):
    """
    Hourglass with Encoder/Decoder and skip connections.
    Checkpoint key structure: encoder.down_blocks.*, decoder.up_blocks.*, decoder.conv.*, decoder.norm.*
    """
    def __init__(self, block_expansion, in_features, max_features, num_blocks):
        super(Hourglass, self).__init__()
        self.encoder = Encoder(block_expansion, in_features, max_features, num_blocks)

        # Encoder dims: [in_features, block_0_out, block_1_out, ..., block_{num_blocks-1}_out]
        enc_dims = [in_features]
        for i in range(num_blocks):
            if i == 0:
                d = min(max_features, block_expansion)
            else:
                d = min(max_features, block_expansion * (2 ** i))
            enc_dims.append(d)

        self.decoder = Decoder(block_expansion, in_features, max_features, num_blocks, enc_dims)
        self.out_filters = self.decoder.conv.out_channels

    def forward(self, x):
        enc_outs = self.encoder(x)
        out = self.decoder(enc_outs)
        return out
