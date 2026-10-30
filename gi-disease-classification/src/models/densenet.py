"""
Baseline Architecture: DenseNet-121
Dense Convolutional Network baseline for endoscopic image classification.
Used as the primary comparative benchmark against the proposed ConvNeXt-Tiny + CBAM model.
"""

try:
    import torch
    import torch.nn as nn
    from torchvision import models
    from torchvision.models import DenseNet121_Weights
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False


if TORCH_AVAILABLE:

    class DenseNetBaseline(nn.Module):
        """
        DenseNet-121 Baseline Model:
        Features reuse via dense block concatenations, adapted with an 8-class head
        for gastrointestinal lesion classification.
        """

        def __init__(
            self,
            num_classes: int = 8,
            pretrained: bool = True,
            dropout_rate: float = 0.3,
        ):
            super().__init__()
            self.num_classes = num_classes

            weights = DenseNet121_Weights.DEFAULT if pretrained else None
            base_model = models.densenet121(weights=weights)

            self.features = base_model.features
            in_features = base_model.classifier.in_features  # 1024

            self.relu = nn.ReLU(inplace=True)
            self.avgpool = nn.AdaptiveAvgPool2d((1, 1))
            self.dropout = nn.Dropout(p=dropout_rate)
            self.classifier = nn.Linear(in_features, num_classes)

        def forward(self, x: torch.Tensor) -> torch.Tensor:
            features = self.features(x)
            out = self.relu(features)
            out = self.avgpool(out)
            out = torch.flatten(out, 1)
            out = self.dropout(out)
            logits = self.classifier(out)
            return logits

        def get_target_layer_for_gradcam(self) -> nn.Module:
            """Return the final dense block layer for Grad-CAM."""
            return self.features.denseblock4

else:
    class DenseNetBaseline:  # type: ignore
        def __init__(self, num_classes: int = 8, pretrained: bool = True):
            self.num_classes = num_classes


def create_densenet_baseline(num_classes: int = 8, pretrained: bool = True) -> "DenseNetBaseline":
    """Factory helper to instantiate DenseNet baseline."""
    return DenseNetBaseline(num_classes=num_classes, pretrained=pretrained)
