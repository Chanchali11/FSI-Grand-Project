import sys
from pathlib import Path
import numpy as np
from PIL import Image

gi_root = Path(__file__).resolve().parent.parent
if str(gi_root) not in sys.path:
    sys.path.insert(0, str(gi_root))

from src.data.dataset import DatasetManager, KVASIR_CLASSES
from src.explainability.gradcam import GradCAM
from src.inference.predict import PredictionService
from src.training.evaluate import ModelEvaluator


def test_dataset_classes_and_sample_generation(tmp_path):
    """Verify all 8 Kvasir classes and sample generation."""
    assert len(KVASIR_CLASSES) == 8
    assert "polyps" in KVASIR_CLASSES
    assert "ulcerative-colitis" in KVASIR_CLASSES

    # Generate synthetic samples
    DatasetManager.generate_sample_endoscopy_dataset(tmp_path, samples_per_class=2)

    # Validate dataset
    cleaned = DatasetManager.validate_and_clean_images(tmp_path)
    assert len(cleaned) == 8
    for cls_name, paths in cleaned.items():
        assert len(paths) == 2


def test_stratified_dataset_splitting():
    """Verify stratified splitting maintains proportion and handles classes evenly."""
    mock_dataset = {cls_name: [f"path/{cls_name}/img_{i}.jpg" for i in range(20)] for cls_name in KVASIR_CLASSES}
    splits = DatasetManager.create_stratified_splits(mock_dataset, train_ratio=0.70, val_ratio=0.15, test_ratio=0.15, seed=42)

    assert len(splits["train"]["paths"]) == 14 * 8
    assert len(splits["val"]["paths"]) == 3 * 8
    assert len(splits["test"]["paths"]) == 3 * 8
    assert len(splits["train"]["labels"]) == len(splits["train"]["paths"])


def test_gradcam_heatmap_and_overlay():
    """Verify Grad-CAM synthetic heatmap generation and image overlay."""
    test_img = Image.new("RGB", (224, 224), color=(180, 80, 80))
    heatmap = GradCAM._generate_synthetic_heatmap((224, 224))

    assert heatmap.shape == (224, 224)
    assert np.max(heatmap) <= 1.0
    assert np.min(heatmap) >= 0.0

    overlay = GradCAM.overlay_heatmap(test_img, heatmap, alpha=0.5, colormap="JET")
    assert isinstance(overlay, Image.Image)
    assert overlay.size == (224, 224)


def test_prediction_service_pipeline():
    """Verify unified prediction service accepts images and produces predictions."""
    service = PredictionService(model_type="convnext_cbam")
    test_img = Image.new("RGB", (224, 224), color=(60, 90, 160))

    result = service.predict(test_img)
    assert "predicted_class" in result
    assert result["predicted_class"] in KVASIR_CLASSES
    assert 0.0 <= result["confidence"] <= 1.0
    assert len(result["all_probabilities"]) == 8
    assert result["overlay_image"] is not None
    assert result["latency_ms"] >= 0.0


def test_benchmark_metrics():
    """Verify baseline and proposed model benchmark integrity."""
    benchmarks = ModelEvaluator.get_benchmark_comparison()
    assert "DenseNet-121 (Baseline)" in benchmarks
    assert "ConvNeXt-Tiny + CBAM (Proposed)" in benchmarks

    proposed = benchmarks["ConvNeXt-Tiny + CBAM (Proposed)"]
    baseline = benchmarks["DenseNet-121 (Baseline)"]

    assert proposed["accuracy"] > baseline["accuracy"]
    assert proposed["macro_f1"] > baseline["macro_f1"]
    assert proposed["polyp_sensitivity"] > baseline["polyp_sensitivity"]
