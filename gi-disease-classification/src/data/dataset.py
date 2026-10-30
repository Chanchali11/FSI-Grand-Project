"""
Dataset Management, Validation, and Preprocessing for Gastrointestinal Endoscopy
Supports Kvasir v1/v2 image classification with stratified splits,
corrupt image verification, and training data augmentation.
"""

import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
from PIL import Image, ImageDraw

try:
    import torch
    from torch.utils.data import Dataset, DataLoader
    from torchvision import transforms
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False


KVASIR_CLASSES = [
    "dyed-lifted-polyps",
    "dyed-resection-margins",
    "esophagitis",
    "normal-cecum",
    "normal-pylorus",
    "normal-z-line",
    "polyps",
    "ulcerative-colitis",
]

CLASS_TO_IDX = {cls_name: i for i, cls_name in enumerate(KVASIR_CLASSES)}
IDX_TO_CLASS = {i: cls_name for i, cls_name in enumerate(KVASIR_CLASSES)}


def get_transforms(image_size: int = 224, is_training: bool = True):
    """
    Produce standard PyTorch data transformation pipeline.
    Applies aggressive medical data augmentation during training to prevent overfitting.
    """
    if not TORCH_AVAILABLE:
        return None

    mean = [0.485, 0.456, 0.406]
    std = [0.229, 0.224, 0.225]

    if is_training:
        return transforms.Compose([
            transforms.Resize((image_size, image_size)),
            transforms.RandomHorizontalFlip(p=0.5),
            transforms.RandomVerticalFlip(p=0.5),
            transforms.RandomRotation(degrees=15),
            transforms.ColorJitter(brightness=0.15, contrast=0.15, saturation=0.1),
            transforms.ToTensor(),
            transforms.Normalize(mean=mean, std=std),
        ])
    else:
        return transforms.Compose([
            transforms.Resize((image_size, image_size)),
            transforms.ToTensor(),
            transforms.Normalize(mean=mean, std=std),
        ])


if TORCH_AVAILABLE:

    class KvasirDataset(Dataset):
        """
        PyTorch Dataset for Gastrointestinal Endoscopy classification.
        """

        def __init__(self, image_paths: List[str], labels: List[int], transform=None):
            self.image_paths = image_paths
            self.labels = labels
            self.transform = transform

        def __len__(self) -> int:
            return len(self.image_paths)

        def __getitem__(self, idx: int) -> Tuple[torch.Tensor, int]:
            img_path = self.image_paths[idx]
            image = Image.open(img_path).convert("RGB")
            label = self.labels[idx]

            if self.transform:
                image = self.transform(image)

            return image, label

else:
    class KvasirDataset:  # type: ignore
        def __init__(self, image_paths: List[str], labels: List[int], transform=None):
            self.image_paths = image_paths
            self.labels = labels


class DatasetManager:
    """
    Orchestrates dataset integrity validation, stratified train/val/test splitting,
    and synthetic dataset synthesis for demonstration and testing.
    """

    @staticmethod
    def validate_and_clean_images(data_dir: str | Path) -> Dict[str, List[str]]:
        """
        Scan directory for corrupt, empty, or unreadable images.
        Returns a dictionary mapping class names to valid file paths.
        """
        data_dir = Path(data_dir)
        valid_dataset = {}

        for cls_name in KVASIR_CLASSES:
            cls_folder = data_dir / cls_name
            if not cls_folder.exists():
                continue

            valid_images = []
            for file_path in cls_folder.glob("*.*"):
                if file_path.suffix.lower() not in [".jpg", ".jpeg", ".png", ".bmp"]:
                    continue

                # Check corruption
                try:
                    if file_path.stat().st_size == 0:
                        continue
                    with Image.open(file_path) as img:
                        img.verify()
                    valid_images.append(str(file_path))
                except Exception:
                    # Skip corrupted file
                    continue

            valid_dataset[cls_name] = sorted(valid_images)

        return valid_dataset

    @staticmethod
    def create_stratified_splits(
        class_image_dict: Dict[str, List[str]],
        train_ratio: float = 0.70,
        val_ratio: float = 0.15,
        test_ratio: float = 0.15,
        seed: int = 42,
    ) -> Dict[str, Dict[str, List]]:
        """
        Perform deterministic stratified splitting to maintain class balance across splits.
        """
        np.random.seed(seed)
        splits = {
            "train": {"paths": [], "labels": []},
            "val": {"paths": [], "labels": []},
            "test": {"paths": [], "labels": []},
        }

        for cls_name, paths in class_image_dict.items():
            if not paths:
                continue

            shuffled_paths = np.array(paths)
            indices = np.random.permutation(len(shuffled_paths))
            shuffled_paths = shuffled_paths[indices].tolist()

            n_total = len(shuffled_paths)
            n_train = int(n_total * train_ratio)
            n_val = int(n_total * val_ratio)

            train_paths = shuffled_paths[:n_train]
            val_paths = shuffled_paths[n_train:n_train + n_val]
            test_paths = shuffled_paths[n_train + n_val:]

            cls_idx = CLASS_TO_IDX.get(cls_name, 0)

            splits["train"]["paths"].extend(train_paths)
            splits["train"]["labels"].extend([cls_idx] * len(train_paths))

            splits["val"]["paths"].extend(val_paths)
            splits["val"]["labels"].extend([cls_idx] * len(val_paths))

            splits["test"]["paths"].extend(test_paths)
            splits["test"]["labels"].extend([cls_idx] * len(test_paths))

        return splits

    @staticmethod
    def generate_sample_endoscopy_dataset(base_dir: str | Path, samples_per_class: int = 4):
        """
        Synthesize realistic mock endoscopic images for all 8 categories
        for immediate local testing and demonstration.
        """
        base_dir = Path(base_dir)
        base_dir.mkdir(parents=True, exist_ok=True)

        # Visual styling per class: (base_color, lesion_color, pattern_name)
        class_visuals = {
            "dyed-lifted-polyps": ((60, 90, 160), (30, 50, 120), "dyed_contour"),
            "dyed-resection-margins": ((50, 80, 140), (20, 30, 60), "indigo_margin"),
            "esophagitis": ((180, 70, 70), (220, 40, 40), "linear_streak"),
            "normal-cecum": ((170, 90, 80), (130, 60, 50), "orifice"),
            "normal-pylorus": ((160, 95, 85), (80, 40, 35), "pyloric_aperture"),
            "normal-z-line": ((175, 100, 90), (200, 120, 110), "squamocolumnar"),
            "polyps": ((165, 85, 75), (205, 55, 65), "elevated_protuberance"),
            "ulcerative-colitis": ((190, 65, 65), (230, 20, 30), "friable_erythema"),
        }

        for cls_name, (bg_color, fg_color, pattern) in class_visuals.items():
            cls_folder = base_dir / cls_name
            cls_folder.mkdir(parents=True, exist_ok=True)

            for i in range(1, samples_per_class + 1):
                img = Image.new("RGB", (224, 224), color=bg_color)
                draw = ImageDraw.Draw(img)

                # Vignette / circular endoscopic aperture effect
                draw.ellipse([(12, 12), (212, 212)], outline=(30, 15, 15), width=8)

                # Lesion feature
                if pattern in ("dyed_contour", "indigo_margin"):
                    draw.ellipse([(70, 70), (155, 150)], fill=fg_color, outline=(20, 20, 80), width=3)
                elif pattern in ("elevated_protuberance", "friable_erythema"):
                    draw.ellipse([(65, 60), (160, 165)], fill=fg_color, outline=(220, 40, 50), width=2)
                elif pattern == "pyloric_aperture":
                    draw.ellipse([(85, 85), (140, 140)], fill=fg_color)
                else:
                    draw.line([(50, 110), (175, 110)], fill=fg_color, width=12)

                # Add endoscopic timestamp overlay
                draw.text((20, 22), f"KVASIR-DEMO-{cls_name[:3].upper()}-{i:02d}", fill=(240, 240, 240))

                img.save(cls_folder / f"sample_{i:02d}.jpg", quality=92)
