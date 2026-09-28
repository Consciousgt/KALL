"""
run_ml.py
=========
Train and evaluate the CNN concealed-object detector.

Run this AFTER run_physics.py has been executed at least once (to confirm
the physics pipeline works).

Usage:
    python run_ml.py [--samples N] [--epochs E]

The script will:
  1. Generate N synthetic (image, label) pairs using the wideband
     reconstruction pipeline (saved to results/dataset/).
  2. Train the ConvDetector for E epochs.
  3. Evaluate on a held-out test set and print metrics.
  4. Save training curves and example detections to results/.
"""

import argparse
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path

RESULTS_DIR = Path(__file__).parent / "results"
DATASET_DIR = RESULTS_DIR / "dataset"
RESULTS_DIR.mkdir(exist_ok=True)

# ---------------------------------------------------------------------------
# Arg parsing
# ---------------------------------------------------------------------------
parser = argparse.ArgumentParser(description="Train the mmwave CNN detector")
parser.add_argument("--samples", type=int, default=300,
                    help="Total dataset size (default: 300)")
parser.add_argument("--epochs", type=int, default=20,
                    help="Training epochs (default: 20)")
parser.add_argument("--seed", type=int, default=42)
args = parser.parse_args()

# ---------------------------------------------------------------------------
# Imports (after arg parse so --help works without torch)
# ---------------------------------------------------------------------------
try:
    import torch
except ImportError:
    raise SystemExit("PyTorch is required for the ML phase.  Install it via:\n"
                     "  pip install torch")

from ml.dataset import generate_dataset, MmwaveDataset, DATASET_CONFIG
from ml.detector import ConvDetector, train_detector, evaluate_detector

print("=" * 60)
print("mmwave-imaging - CNN Detector Training")
print("=" * 60)
print(f"  Dataset size: {args.samples} samples")
print(f"  Epochs:       {args.epochs}")
print(f"  Device:       {'cuda' if torch.cuda.is_available() else 'cpu'}")
print()

# ---------------------------------------------------------------------------
# Step 1: Generate or load dataset
# ---------------------------------------------------------------------------
images_path = DATASET_DIR / "images.npy"
labels_path = DATASET_DIR / "labels.npy"

if images_path.exists() and labels_path.exists():
    print("Loading cached dataset from results/dataset/ ...")
    images = np.load(images_path)
    labels = np.load(labels_path)
    if len(images) != args.samples:
        print(f"  Cached size ({len(images)}) != requested ({args.samples}). Regenerating...")
        images, labels = generate_dataset(
            n_samples=args.samples,
            seed=args.seed,
            save_dir=DATASET_DIR,
            verbose=True,
        )
else:
    print(f"Generating {args.samples} samples (this may take several minutes)...")
    images, labels = generate_dataset(
        n_samples=args.samples,
        seed=args.seed,
        save_dir=DATASET_DIR,
        verbose=True,
    )

print(f"  Dataset: {images.shape}  labels: {labels.shape}")
print(f"  Threat: {labels.sum()} / Clean: {(labels==0).sum()}")
print()

# ---------------------------------------------------------------------------
# Step 2: Build dataset and split
# ---------------------------------------------------------------------------
full_dataset = MmwaveDataset(images, labels)

# 70 / 15 / 15 train / val / test split
n_total  = len(full_dataset)
n_test   = max(1, int(n_total * 0.15))
n_rest   = n_total - n_test
train_val_ds, test_ds = torch.utils.data.random_split(
    full_dataset, [n_rest, n_test],
    generator=torch.Generator().manual_seed(args.seed),
)

# ---------------------------------------------------------------------------
# Step 3: Train
# ---------------------------------------------------------------------------
print("Training ConvDetector...")
model, history = train_detector(
    dataset=train_val_ds,
    n_epochs=args.epochs,
    batch_size=32,
    lr=1e-3,
    val_fraction=0.15 / 0.85,   # 15% of original from remaining 85%
    seed=args.seed,
    save_path=RESULTS_DIR / "detector_weights.pt",
    verbose=True,
)
print()

# ---------------------------------------------------------------------------
# Step 4: Evaluate on test set
# ---------------------------------------------------------------------------
print("Evaluating on test set...")
test_full_ds = MmwaveDataset(
    images[test_ds.indices], labels[test_ds.indices]
)
metrics = evaluate_detector(model, test_full_ds)
print(f"  Accuracy:  {metrics['accuracy']:.3f}")
print(f"  Precision: {metrics['precision']:.3f}")
print(f"  Recall:    {metrics['recall']:.3f}")
print(f"  F1:        {metrics['f1']:.3f}")
print(f"  Confusion matrix (rows=true, cols=pred):")
print(f"    {metrics['confusion_matrix']}")
print()

# ---------------------------------------------------------------------------
# Step 5: Save plots
# ---------------------------------------------------------------------------
print("Saving plots to results/...")

# Training curves
fig, axes = plt.subplots(1, 2, figsize=(10, 4))
axes[0].plot(history["train_loss"], label="Train")
axes[0].plot(history["val_loss"],   label="Val")
axes[0].set_xlabel("Epoch"); axes[0].set_ylabel("Loss")
axes[0].set_title("Training / Validation Loss")
axes[0].legend(); axes[0].grid(True, alpha=0.3)

axes[1].plot(history["val_acc"])
axes[1].set_xlabel("Epoch"); axes[1].set_ylabel("Accuracy")
axes[1].set_title("Validation Accuracy")
axes[1].grid(True, alpha=0.3)
fig.tight_layout()
fig.savefig(RESULTS_DIR / "training_curves.png", dpi=150, bbox_inches='tight')
plt.close(fig)

# Example detections (first 8 test images)
fig, axes = plt.subplots(2, 4, figsize=(12, 6))
probs = metrics["y_prob"]
preds = metrics["y_pred"]
trues = metrics["y_true"]
for idx, ax in enumerate(axes.flat):
    if idx >= len(test_full_ds):
        ax.axis('off')
        continue
    img, lbl = test_full_ds[idx]
    img_np = img.squeeze().numpy()
    ax.imshow(img_np, cmap='hot', aspect='equal')
    color = 'green' if preds[idx] == trues[idx] else 'red'
    ax.set_title(
        f"True: {'Threat' if trues[idx] else 'Clean'}\n"
        f"Pred: {'Threat' if preds[idx] else 'Clean'} ({probs[idx]:.2f})",
        fontsize=8, color=color,
    )
    ax.axis('off')
fig.suptitle("Example Detections (green=correct, red=wrong)", fontsize=11)
fig.tight_layout()
fig.savefig(RESULTS_DIR / "example_detections.png", dpi=150, bbox_inches='tight')
plt.close(fig)

print("  training_curves.png")
print("  example_detections.png")
print("  detector_weights.pt")
print()
print("Done.")
