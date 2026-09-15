"""
ml/detector.py
==============
Lightweight CNN for binary concealed-object classification.

Architecture
------------
The network is deliberately small — this is a signal-processing portfolio
project; the CNN is the "AI/ML" layer on top of the physics engine.

    Input : (B, 1, H, W)   float32 MIP image, normalised to [0, 1]

    Block 1: Conv2d(1→16, 3×3, pad=1) → BatchNorm → ReLU → MaxPool(2)
    Block 2: Conv2d(16→32, 3×3, pad=1) → BatchNorm → ReLU → MaxPool(2)
    Block 3: Conv2d(32→64, 3×3, pad=1) → BatchNorm → ReLU → MaxPool(2)
    Head   : AdaptiveAvgPool2d(4×4) → Flatten → Linear(1024→128) → ReLU
             → Dropout(0.4) → Linear(128→2)

    Output: raw logits for [clean, threat] — use softmax for probabilities.

Training details
----------------
- Optimizer: Adam, lr=1e-3, weight_decay=1e-4
- Loss: CrossEntropyLoss
- LR schedule: ReduceLROnPlateau (patience=5)
- Trained for up to 30 epochs, early stopping on validation loss.
- Input shape is inferred from the first batch — no hardcoded H/W.
"""

from __future__ import annotations

import numpy as np
from pathlib import Path
from typing import Optional

try:
    import torch
    import torch.nn as nn
    import torch.optim as optim
    from torch.utils.data import DataLoader, random_split
    _TORCH_AVAILABLE = True
except ImportError:
    _TORCH_AVAILABLE = False


# ---------------------------------------------------------------------------
# Model definition
# ---------------------------------------------------------------------------

if _TORCH_AVAILABLE:
    class ConvDetector(nn.Module):
        """Small CNN binary classifier for concealed-object detection.

        Parameters
        ----------
        n_classes : int
            Number of output classes (default 2: clean / threat).
        """

        def __init__(self, n_classes: int = 2):
            super().__init__()

            def _block(in_ch, out_ch):
                return nn.Sequential(
                    nn.Conv2d(in_ch, out_ch, kernel_size=3, padding=1, bias=False),
                    nn.BatchNorm2d(out_ch),
                    nn.ReLU(inplace=True),
                    nn.MaxPool2d(2),
                )

            self.features = nn.Sequential(
                _block(1, 16),
                _block(16, 32),
                _block(32, 64),
            )
            self.pool = nn.AdaptiveAvgPool2d((4, 4))
            self.classifier = nn.Sequential(
                nn.Flatten(),
                nn.Linear(64 * 4 * 4, 128),
                nn.ReLU(inplace=True),
                nn.Dropout(0.4),
                nn.Linear(128, n_classes),
            )

        def forward(self, x: "torch.Tensor") -> "torch.Tensor":
            x = self.features(x)
            x = self.pool(x)
            x = self.classifier(x)
            return x


# ---------------------------------------------------------------------------
# Training loop
# ---------------------------------------------------------------------------

def train_detector(
    dataset,
    n_epochs: int = 30,
    batch_size: int = 32,
    lr: float = 1e-3,
    val_fraction: float = 0.2,
    seed: int = 42,
    save_path: str | Path | None = None,
    device: str | None = None,
    verbose: bool = True,
) -> tuple["ConvDetector", dict]:
    """Train the ConvDetector on a MmwaveDataset.

    Parameters
    ----------
    dataset : MmwaveDataset
        Full dataset (will be split into train / val).
    n_epochs : int
        Maximum training epochs.
    batch_size : int
        Mini-batch size.
    lr : float
        Initial Adam learning rate.
    val_fraction : float
        Fraction of dataset held out for validation.
    seed : int
        Random seed for train/val split.
    save_path : path-like, optional
        If provided, saves the best model weights here as a .pt file.
    device : str, optional
        'cpu', 'cuda', or 'mps'.  Auto-detected if None.
    verbose : bool
        Print per-epoch metrics.

    Returns
    -------
    model : ConvDetector
        Trained model (weights from the epoch with lowest val loss).
    history : dict
        Keys: 'train_loss', 'val_loss', 'val_acc' — lists of per-epoch values.
    """
    if not _TORCH_AVAILABLE:
        raise ImportError("PyTorch is required to train the detector.")

    if device is None:
        device = (
            "cuda" if torch.cuda.is_available()
            else "mps" if torch.backends.mps.is_available()
            else "cpu"
        )

    torch.manual_seed(seed)
    n_val = max(1, int(len(dataset) * val_fraction))
    n_train = len(dataset) - n_val
    train_ds, val_ds = random_split(
        dataset, [n_train, n_val],
        generator=torch.Generator().manual_seed(seed),
    )

    train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True)
    val_loader   = DataLoader(val_ds,   batch_size=batch_size, shuffle=False)

    model = ConvDetector(n_classes=2).to(device)
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters(), lr=lr, weight_decay=1e-4)
    scheduler = optim.lr_scheduler.ReduceLROnPlateau(
        optimizer, mode='min', patience=5, factor=0.5, verbose=False,
    )

    history = {"train_loss": [], "val_loss": [], "val_acc": []}
    best_val_loss = float("inf")
    best_weights = None

    for epoch in range(1, n_epochs + 1):
        # --- Training ---
        model.train()
        running_loss = 0.0
        for imgs, lbls in train_loader:
            imgs, lbls = imgs.to(device), lbls.to(device)
            optimizer.zero_grad()
            logits = model(imgs)
            loss = criterion(logits, lbls)
            loss.backward()
            optimizer.step()
            running_loss += loss.item() * len(imgs)
        train_loss = running_loss / n_train

        # --- Validation ---
        model.eval()
        val_loss = 0.0
        correct = 0
        with torch.no_grad():
            for imgs, lbls in val_loader:
                imgs, lbls = imgs.to(device), lbls.to(device)
                logits = model(imgs)
                val_loss += criterion(logits, lbls).item() * len(imgs)
                preds = logits.argmax(dim=1)
                correct += (preds == lbls).sum().item()
        val_loss /= n_val
        val_acc = correct / n_val

        scheduler.step(val_loss)
        history["train_loss"].append(train_loss)
        history["val_loss"].append(val_loss)
        history["val_acc"].append(val_acc)

        if val_loss < best_val_loss:
            best_val_loss = val_loss
            import copy
            best_weights = copy.deepcopy(model.state_dict())

        if verbose and (epoch == 1 or epoch % 5 == 0 or epoch == n_epochs):
            print(
                f"  Epoch {epoch:3d}/{n_epochs}  "
                f"train_loss={train_loss:.4f}  "
                f"val_loss={val_loss:.4f}  "
                f"val_acc={val_acc:.3f}"
            )

    # Restore best weights
    if best_weights is not None:
        model.load_state_dict(best_weights)

    if save_path is not None:
        save_path = Path(save_path)
        save_path.parent.mkdir(parents=True, exist_ok=True)
        torch.save(model.state_dict(), save_path)
        if verbose:
            print(f"Best model saved to {save_path}")

    return model, history


# ---------------------------------------------------------------------------
# Evaluation
# ---------------------------------------------------------------------------

def evaluate_detector(
    model,
    dataset,
    batch_size: int = 32,
    device: str | None = None,
) -> dict:
    """Evaluate the trained detector and return per-class metrics.

    Parameters
    ----------
    model : ConvDetector
        Trained model.
    dataset : MmwaveDataset
        Evaluation dataset.
    batch_size : int
    device : str, optional

    Returns
    -------
    metrics : dict with keys:
        'accuracy', 'precision', 'recall', 'f1',
        'confusion_matrix' (2×2 ndarray),
        'y_true', 'y_pred', 'y_prob'
    """
    if not _TORCH_AVAILABLE:
        raise ImportError("PyTorch is required.")

    if device is None:
        device = (
            "cuda" if torch.cuda.is_available()
            else "mps" if torch.backends.mps.is_available()
            else "cpu"
        )

    loader = DataLoader(dataset, batch_size=batch_size, shuffle=False)
    model.eval().to(device)

    all_preds, all_probs, all_true = [], [], []
    with torch.no_grad():
        for imgs, lbls in loader:
            imgs = imgs.to(device)
            logits = model(imgs)
            probs = torch.softmax(logits, dim=1)[:, 1].cpu().numpy()
            preds = logits.argmax(dim=1).cpu().numpy()
            all_preds.append(preds)
            all_probs.append(probs)
            all_true.append(lbls.numpy())

    y_true = np.concatenate(all_true)
    y_pred = np.concatenate(all_preds)
    y_prob = np.concatenate(all_probs)

    # Confusion matrix (rows=true, cols=pred)
    cm = np.zeros((2, 2), dtype=int)
    for t, p in zip(y_true, y_pred):
        cm[t, p] += 1

    tp = cm[1, 1]
    fp = cm[0, 1]
    fn = cm[1, 0]
    tn = cm[0, 0]

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall    = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1        = (2 * precision * recall / (precision + recall)
                 if (precision + recall) > 0 else 0.0)
    accuracy  = (tp + tn) / len(y_true)

    return {
        "accuracy": accuracy,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "confusion_matrix": cm,
        "y_true": y_true,
        "y_pred": y_pred,
        "y_prob": y_prob,
    }

else:
    # Stubs for environments without PyTorch
    class ConvDetector:  # type: ignore[no-redef]
        def __init__(self, *a, **kw):
            raise ImportError("PyTorch is required.")

    def train_detector(*a, **kw):  # type: ignore[misc]
        raise ImportError("PyTorch is required.")

    def evaluate_detector(*a, **kw):  # type: ignore[misc]
        raise ImportError("PyTorch is required.")
