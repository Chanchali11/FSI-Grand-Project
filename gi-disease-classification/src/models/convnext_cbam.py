"""
Proposed Architecture: ConvNeXt-Tiny + CBAM Attention
Combines modern pure-convolutional visual representations with adaptive
channel and spatial attention refinement for endoscopic gastrointestinal lesion classification.
"""

from typing import Optional

try:
    import torch
    import torch.nn as nn
    from torchvision import models
    from torchvision.models import ConvNeXt_Tiny_Weights
    from src.models.cbam import CBAM
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False


if TORCH_AVAILABLE:

    class ConvNeXtTinyCBAM(nn.Module):
        """
        ConvNeXt-Tiny backbone enhanced with a Convolutional Block Attention Module (CBAM)
        inserted before global average pooling and classification.

        Pipeline:
            Input [B, 3, 224, 224]
              ↓
            ConvNeXt-Tiny Features [B, 768, 7, 7]
              ↓
            CBAM Attention (Channel + Spatial Refinement) [B, 768, 7, 7]
              ↓
            Adaptive Global Average Pooling [B, 768, 1, 1]
              ↓
            Flatten & Dropout
              ↓
            Linear Classification Head [B, num_classes]
        """

        def __init__(
            self,
            num_classes: int = 8,
            pretrained: bool = True,
            cbam_reduction_ratio: int = 16,
            cbam_kernel_size: int = 7,
            dropout_rate: float = 0.2,
        ):
            super().__init__()
            self.num_classes = num_classes

            # Load pretrained ConvNeXt-Tiny backbone
            weights = ConvNeXt_Tiny_Weights.DEFAULT if pretrained else None
            base_model = models.convnext_tiny(weights=weights)

            # Feature extractor up to final stage
            self.features = base_model.features
            in_features = 768  # ConvNeXt-Tiny final channel dimension

            # Attention Module
            self.cbam = CBAM(
                in_planes=in_features,
                reduction_ratio=cbam_reduction_ratio,
                spatial_kernel_size=cbam_kernel_size,
            )

            # Global Pooling & Head
            self.avgpool = nn.AdaptiveAvgPool2d((1, 1))
            self.dropout = nn.Dropout(p=dropout_rate)
            self.classifier = nn.Sequential(
                nn.Flatten(),
                self.dropout,
                nn.Linear(in_features, num_classes),
            )

        def forward(self, x: torch.Tensor) -> torch.Tensor:
            x = self.features(x)
            x = self.cbam(x)
            x = self.avgpool(x)
            logits = self.classifier(x)
            return logits

        def get_target_layer_for_gradcam(self) -> nn.Module:
            """Return the target convolutional feature layer used for Grad-CAM explanations."""
            # Target the output of the CBAM module or the last feature stage
            return self.cbam

else:
    class ConvNeXtTinyCBAM:  # type: ignore
        def __init__(self, num_classes: int = 8, pretrained: bool = True):
            self.num_classes = num_classes


def create_convnext_cbam_model(num_classes: int = 8, pretrained: bool = True) -> "ConvNeXtTinyCBAM":
    """Factory helper to instantiate ConvNeXt-Tiny + CBAM."""
    return ConvNeXtTinyCBAM(num_classes=num_classes, pretrained=pretrained)
