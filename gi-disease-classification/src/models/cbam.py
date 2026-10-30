"""
Convolutional Block Attention Module (CBAM)
Reference: Woo et al., "CBAM: Convolutional Block Attention Module", ECCV 2018.

CBAM sequentially infers attention maps along two separate dimensions:
channel and spatial, then the attention maps are multiplied to the input
feature map for adaptive feature refinement.
"""

try:
    import torch
    import torch.nn as nn
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False


if TORCH_AVAILABLE:

    class ChannelAttention(nn.Module):
        """
        Channel Attention Module:
        Aggregates spatial information using both Average Pooling and Max Pooling,
        processes them through a shared Multi-Layer Perceptron (MLP), and applies
        a sigmoid activation to generate channel attention weights.
        """

        def __init__(self, in_planes: int, reduction_ratio: int = 16):
            super().__init__()
            self.avg_pool = nn.AdaptiveAvgPool2d(1)
            self.max_pool = nn.AdaptiveMaxPool2d(1)

            reduced_planes = max(in_planes // reduction_ratio, 8)
            self.mlp = nn.Sequential(
                nn.Conv2d(in_planes, reduced_planes, kernel_size=1, bias=False),
                nn.ReLU(inplace=True),
                nn.Conv2d(reduced_planes, in_planes, kernel_size=1, bias=False),
            )
            self.sigmoid = nn.Sigmoid()

        def forward(self, x: torch.Tensor) -> torch.Tensor:
            avg_out = self.mlp(self.avg_pool(x))
            max_out = self.mlp(self.max_pool(x))
            channel_weights = self.sigmoid(avg_out + max_out)
            return x * channel_weights


    class SpatialAttention(nn.Module):
        """
        Spatial Attention Module:
        Compresses channel information by computing average and max values across
        the channel axis, concatenates them into a 2-channel spatial map, and applies
        a standard 7x7 convolution followed by sigmoid activation.
        """

        def __init__(self, kernel_size: int = 7):
            super().__init__()
            assert kernel_size in (3, 7), "Kernel size must be 3 or 7"
            padding = 3 if kernel_size == 7 else 1

            self.conv = nn.Conv2d(2, 1, kernel_size=kernel_size, padding=padding, bias=False)
            self.sigmoid = nn.Sigmoid()

        def forward(self, x: torch.Tensor) -> torch.Tensor:
            avg_out = torch.mean(x, dim=1, keepdim=True)
            max_out, _ = torch.max(x, dim=1, keepdim=True)
            concat_map = torch.cat([avg_out, max_out], dim=1)
            spatial_weights = self.sigmoid(self.conv(concat_map))
            return x * spatial_weights


    class CBAM(nn.Module):
        """
        Complete CBAM block combining Channel Attention followed by Spatial Attention.
        Feature Refinement Pipeline:
            F -> ChannelAttention(F) -> F' -> SpatialAttention(F') -> F''
        """

        def __init__(self, in_planes: int, reduction_ratio: int = 16, spatial_kernel_size: int = 7):
            super().__init__()
            self.channel_attention = ChannelAttention(in_planes, reduction_ratio=reduction_ratio)
            self.spatial_attention = SpatialAttention(kernel_size=spatial_kernel_size)

        def forward(self, x: torch.Tensor) -> torch.Tensor:
            x_out = self.channel_attention(x)
            x_out = self.spatial_attention(x_out)
            return x_out

else:
    # Fallback placeholder if PyTorch is not yet installed in the current environment
    class CBAM:  # type: ignore
        def __init__(self, in_planes: int = 768, reduction_ratio: int = 16, spatial_kernel_size: int = 7):
            self.in_planes = in_planes
            self.reduction_ratio = reduction_ratio
            self.spatial_kernel_size = spatial_kernel_size
