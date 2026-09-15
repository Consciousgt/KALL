"""
ml/dataset.py
=============
Generates a synthetic labelled dataset for the concealed-object detector.

Each sample is a 2-D max-intensity-projection (MIP) image derived from the
wideband reconstruction of a simulated scene.  The label is binary:
  0 = clean (no concealed object)
  1 = concealed object present

Dataset generation pipeline (per sample):
  1. Randomly decide clean vs. threat (50 / 50 split).
  2. If threat: sample a random weapon-like target (position, depth, size).
     If clean: empty scene or a very small, low-reflectivity clutter scatter.
  3. Simulate scattered-field data with small additive noise.
  4. Run the wideband reconstruction.
  5. Take the z-MIP → (nx, ny) image.
  6. Normalise to [0, 1].
  7. Store (image, label) in memory or save to disk as .npy.

Augmentation applied per sample:
  - Target x/y position: uniform over ±20% of aperture extent
  - Target depth z: uniform in [0.3, 0.7] m
  - Target width / height: ±30% variation
  - Reflectivity amplitude: uniform in [0.5, 1.5]
  - Noise σ: uniform in [0.0, 0.05]
"""

from __future__ import annotations

import os
import numpy as np
from pathlib import Path
from typing import Callable

from simulation.targets import make_weapon_scene, make_clean_scene
from simulation.array_sim import ApertureConfig, simulate_scattered_field
from reconstruction.wideband import reconstruct_wideband

try:
    import torch
    from torch.utils.data import Dataset as TorchDataset
    _TORCH_AVAILABLE = True
except ImportError:
    _TORCH_AVAILABLE = False


# ---------------------------------------------------------------------------
# Dataset generation config
# ---------------------------------------------------------------------------

# Lightweight config for dataset generation (balance between speed and fidelity)
DATASET_CONFIG = ApertureConfig(
    f_min=27e9,
    f_max=33e9,
    n_freq=64,
    aperture_x=0.5,
    aperture_y=0.5,
    noise_std=0.0,   # noise added per-sample below
)


def _generate_one_sample(
    label: int,
    rng: np.random.Generator,
    config: ApertureConfig,
    focus_depth: float = 0.25,
) -> np.ndarray:
    """Generate a single (nx, ny) normalised MIP image.

    Parameters
    ----------
    label : int
        0 = clean, 1 = threat.
    rng : numpy Generator
        Shared RNG for reproducibility.
    config : ApertureConfig
        Base aperture / frequency config (noise_std may be overridden).
    focus_depth : float
        Reference depth passed to the wideband reconstructor.

    Returns
    -------
    image : ndarray, shape (nx, ny), float32, values in [0, 1]
    """
    if label == 1:
        # --- Threat scene: weapon-like rectangular cluster of point scatterers ---
        z_tgt     = rng.uniform(0.30, 0.70)
        x_center  = rng.uniform(-0.15, 0.15)
        y_center  = rng.uniform(-0.15, 0.15)
        width     = rng.uniform(0.02, 0.06)    # 2–6 cm (narrow weapon)
        height    = rng.uniform(0.08, 0.16)   # 8–16 cm (long weapon)
        amplitude = rng.uniform(0.5, 1.5)

        scene = make_weapon_scene(
            z=z_tgt,
            width=width,
            height=height,
            nx_pts=4,
            ny_pts=8,
            x_center=x_center,
            y_center=y_center,
            amplitude=complex(amplitude),
            rng=rng,
        )
    else:
        # --- Clean scene: empty or tiny low-reflectivity clutter ---
        scene = make_clean_scene()

    # Per-sample noise
    noise_std = rng.uniform(0.0, 0.05)
    # Build a fresh config with this noise level
    cfg = ApertureConfig(
        f_min=config.f_min,
        f_max=config.f_max,
        n_freq=config.n_freq,
        aperture_x=config.aperture_x,
        aperture_y=config.aperture_y,
        noise_std=noise_std,
    )

    s = simulate_scattered_field(scene, cfg, rng=rng)
    f_vol, _, _, _ = reconstruct_wideband(
        s, cfg.x_arr, cfg.y_arr, cfg.freqs, focus_depth=focus_depth,
    )

    # Max-intensity projection along z
    mip = np.max(np.abs(f_vol), axis=2).astype(np.float32)  # (nx, ny)

    # Normalise to [0, 1]
    mip_max = mip.max()
    if mip_max > 0:
        mip = mip / mip_max

    return mip


def generate_dataset(
    n_samples: int = 500,
    seed: int = 42,
    save_dir: str | Path | None = None,
    config: ApertureConfig = DATASET_CONFIG,
    focus_depth: float = 0.25,
    verbose: bool = True,
) -> tuple[np.ndarray, np.ndarray]:
    """Generate a synthetic labelled dataset.

    Parameters
    ----------
    n_samples : int
        Total number of samples (50 / 50 class split).
    seed : int
        Master random seed for reproducibility.
    save_dir : path-like, optional
        If provided, saves ``images.npy`` and ``labels.npy`` to this directory.
    config : ApertureConfig
        Aperture and frequency sweep configuration.
    focus_depth : float
        Reference depth for wideband reconstruction.
    verbose : bool
        Print progress every 10%.

    Returns
    -------
    images : ndarray, shape (n_samples, nx, ny), float32
    labels : ndarray, shape (n_samples,), int64
    """
    rng = np.random.default_rng(seed)
    labels = np.array([i % 2 for i in range(n_samples)], dtype=np.int64)
    rng.shuffle(labels)

    nx, ny = config.nx, config.ny
    images = np.zeros((n_samples, nx, ny), dtype=np.float32)

    report_interval = max(1, n_samples // 10)
    for i in range(n_samples):
        if verbose and i % report_interval == 0:
            print(f"  Generating sample {i+1}/{n_samples}  (label={labels[i]})...")
        images[i] = _generate_one_sample(
            label=int(labels[i]), rng=rng, config=config, focus_depth=focus_depth,
        )

    if save_dir is not None:
        save_dir = Path(save_dir)
        save_dir.mkdir(parents=True, exist_ok=True)
        np.save(save_dir / "images.npy", images)
        np.save(save_dir / "labels.npy", labels)
        if verbose:
            print(f"Dataset saved to {save_dir}")

    return images, labels


# ---------------------------------------------------------------------------
# PyTorch Dataset wrapper
# ---------------------------------------------------------------------------

if _TORCH_AVAILABLE:
    import torch
    from torch.utils.data import Dataset

    class MmwaveDataset(Dataset):
        """PyTorch Dataset wrapping (images, labels) arrays.

        Parameters
        ----------
        images : ndarray, shape (N, H, W), float32
        labels : ndarray, shape (N,), int64
        transform : callable, optional
            Optional transform applied to each image tensor.
        """

        def __init__(
            self,
            images: np.ndarray,
            labels: np.ndarray,
            transform: Callable | None = None,
        ):
            self.images = torch.from_numpy(images).unsqueeze(1)  # (N, 1, H, W)
            self.labels = torch.from_numpy(labels)
            self.transform = transform

        def __len__(self) -> int:
            return len(self.labels)

        def __getitem__(self, idx: int):
            img = self.images[idx]
            lbl = self.labels[idx]
            if self.transform is not None:
                img = self.transform(img)
            return img, lbl

else:
    # Stub so imports don't break without torch
    class MmwaveDataset:  # type: ignore[no-redef]
        def __init__(self, *args, **kwargs):
            raise ImportError("PyTorch is required for MmwaveDataset")
