"""
visualization/plots.py
======================
Plotting helpers for mmwave holographic reconstruction results.

All functions accept complex volumes (|·| is taken internally where needed)
and return matplotlib Figure objects so callers can save or display them.
"""

from __future__ import annotations

import numpy as np
import matplotlib
matplotlib.use("Agg")          # non-interactive backend — safe for scripts/tests
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from mpl_toolkits.mplot3d import Axes3D  # noqa: F401 (needed for 3-D projection)


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _db(arr: np.ndarray, floor_db: float = -40.0) -> np.ndarray:
    """Convert amplitude to dB relative to the maximum, with a noise floor."""
    mag = np.abs(arr)
    mag_max = mag.max()
    if mag_max == 0:
        return np.full_like(mag, floor_db, dtype=float)
    with np.errstate(divide='ignore', invalid='ignore'):
        db = 20 * np.log10(mag / mag_max)
    return np.clip(db, floor_db, 0.0)


# ---------------------------------------------------------------------------
# Public plotting functions
# ---------------------------------------------------------------------------

def plot_mip(
    volume: np.ndarray,
    x_arr: np.ndarray,
    y_arr: np.ndarray,
    title: str = "Max-Intensity Projection (xy)",
    db_floor: float = -30.0,
    figsize: tuple[float, float] = (5, 5),
) -> plt.Figure:
    """2-D max-intensity projection along the z (range) axis.

    Collapses f(x, y, z) → max_z |f(x, y, z)| and displays in dB.

    Parameters
    ----------
    volume : ndarray, shape (nx, ny, nz), complex
        Reconstructed 3-D image volume.
    x_arr, y_arr : ndarray
        Spatial coordinate axes (m).
    title : str
        Plot title.
    db_floor : float
        Dynamic range floor in dB (default −30 dB).
    figsize : tuple
        Figure size in inches.

    Returns
    -------
    fig : matplotlib Figure
    """
    mip = np.max(np.abs(volume), axis=2)   # (nx, ny)
    mip_db = _db(mip, floor_db=db_floor)

    fig, ax = plt.subplots(figsize=figsize)
    extent = [y_arr[0] * 100, y_arr[-1] * 100, x_arr[-1] * 100, x_arr[0] * 100]
    im = ax.imshow(mip_db, extent=extent, aspect='equal',
                   cmap='hot', vmin=db_floor, vmax=0)
    fig.colorbar(im, ax=ax, label='dB re peak')
    ax.set_xlabel("y (cm)")
    ax.set_ylabel("x (cm)")
    ax.set_title(title)
    fig.tight_layout()
    return fig


def plot_depth_slice(
    volume: np.ndarray,
    x_arr: np.ndarray,
    y_arr: np.ndarray,
    z_arr: np.ndarray,
    z_target: float,
    title: str | None = None,
    db_floor: float = -30.0,
    figsize: tuple[float, float] = (5, 5),
) -> plt.Figure:
    """Display a horizontal (x-y) slice at the depth nearest z_target.

    Parameters
    ----------
    volume : ndarray, shape (nx, ny, nz), complex
    z_target : float
        Desired depth (m); the nearest available z slice is used.
    """
    iz = int(np.argmin(np.abs(z_arr - z_target)))
    actual_z = z_arr[iz]
    slice_2d = volume[:, :, iz]
    slice_db = _db(slice_2d, floor_db=db_floor)

    if title is None:
        title = f"Depth slice at z = {actual_z * 100:.1f} cm"

    fig, ax = plt.subplots(figsize=figsize)
    extent = [y_arr[0] * 100, y_arr[-1] * 100, x_arr[-1] * 100, x_arr[0] * 100]
    im = ax.imshow(slice_db, extent=extent, aspect='equal',
                   cmap='hot', vmin=db_floor, vmax=0)
    fig.colorbar(im, ax=ax, label='dB re peak')
    ax.set_xlabel("y (cm)")
    ax.set_ylabel("x (cm)")
    ax.set_title(title)
    fig.tight_layout()
    return fig


def plot_comparison_mip(
    vol_sf: np.ndarray,
    vol_wb: np.ndarray,
    x_arr: np.ndarray,
    y_arr: np.ndarray,
    suptitle: str = "Single-frequency vs Wideband Reconstruction",
    db_floor: float = -30.0,
    figsize: tuple[float, float] = (11, 5),
) -> plt.Figure:
    """Side-by-side MIP comparison: single-frequency image vs wideband image.

    The single-frequency volume should be the 2-D image broadcast to 3-D
    (or the plain 2-D image — a 2-D array also accepted).

    Parameters
    ----------
    vol_sf : ndarray, shape (nx, ny) or (nx, ny, nz)
        Single-frequency reconstruction result.
    vol_wb : ndarray, shape (nx, ny, nz)
        Wideband reconstruction result.
    """
    # Normalise SF to 3-D if needed
    if vol_sf.ndim == 2:
        mip_sf = np.abs(vol_sf)
    else:
        mip_sf = np.max(np.abs(vol_sf), axis=2)

    mip_wb = np.max(np.abs(vol_wb), axis=2)

    # dB scale each independently relative to the wideband peak
    global_max = max(mip_sf.max(), mip_wb.max())
    if global_max == 0:
        global_max = 1.0

    def to_db(arr):
        with np.errstate(divide='ignore', invalid='ignore'):
            db = 20 * np.log10(arr / global_max)
        return np.clip(db, db_floor, 0.0)

    fig, axes = plt.subplots(1, 2, figsize=figsize)
    extent = [y_arr[0] * 100, y_arr[-1] * 100, x_arr[-1] * 100, x_arr[0] * 100]
    kw = dict(extent=extent, aspect='equal', cmap='hot', vmin=db_floor, vmax=0)

    im0 = axes[0].imshow(to_db(mip_sf), **kw)
    axes[0].set_title("Single-frequency (blurred in z)")
    axes[0].set_xlabel("y (cm)")
    axes[0].set_ylabel("x (cm)")
    fig.colorbar(im0, ax=axes[0], label='dB')

    im1 = axes[1].imshow(to_db(mip_wb), **kw)
    axes[1].set_title("Wideband 3-D (focused)")
    axes[1].set_xlabel("y (cm)")
    axes[1].set_ylabel("x (cm)")
    fig.colorbar(im1, ax=axes[1], label='dB')

    fig.suptitle(suptitle, fontsize=12, fontweight='bold')
    fig.tight_layout()
    return fig


def plot_range_profile(
    volume: np.ndarray,
    z_arr: np.ndarray,
    peak_xy: tuple[int, int] | None = None,
    title: str = "Range (depth) profile through peak",
    figsize: tuple[float, float] = (7, 4),
) -> plt.Figure:
    """1-D range profile through the peak of the volume (or a specified voxel).

    Used to measure FWHM and validate range resolution against theory.

    Parameters
    ----------
    volume : ndarray, shape (nx, ny, nz), complex
    peak_xy : (ix, iy) int tuple, optional
        Indices of the (x, y) voxel to profile.  If None, uses the voxel
        with the maximum integrated range energy.
    """
    mag = np.abs(volume)
    if peak_xy is None:
        # Find (ix, iy) at the overall peak
        flat_idx = np.argmax(mag)
        ix, iy, _ = np.unravel_index(flat_idx, mag.shape)
    else:
        ix, iy = peak_xy

    profile = mag[ix, iy, :]   # (nz,)
    profile_db = _db(profile)

    fig, ax = plt.subplots(figsize=figsize)
    ax.plot(z_arr * 100, profile_db, 'b-', linewidth=1.5, label='|f(z)|')
    ax.axhline(-3, color='r', linestyle='--', linewidth=1, label='-3 dB (FWHM)')
    ax.set_xlabel("z (cm)")
    ax.set_ylabel("Amplitude (dB re peak)")
    ax.set_title(title)
    ax.legend()
    ax.grid(True, alpha=0.3)
    ax.set_ylim([-40, 2])
    fig.tight_layout()
    return fig


def plot_3d_scatter(
    volume: np.ndarray,
    x_arr: np.ndarray,
    y_arr: np.ndarray,
    z_arr: np.ndarray,
    threshold_db: float = -6.0,
    title: str = "3-D Reconstructed Volume",
    figsize: tuple[float, float] = (8, 7),
) -> plt.Figure:
    """Sparse 3-D scatter plot of voxels above a threshold.

    Provides an intuitive 3-D view of the reconstructed volume — suitable
    for README / portfolio visualisations.

    Parameters
    ----------
    volume : ndarray, shape (nx, ny, nz), complex
    threshold_db : float
        Only voxels with amplitude > threshold_db (relative to peak) are plotted.
    """
    mag_db = _db(np.abs(volume))
    mask = mag_db > threshold_db

    xs, ys, zs = np.where(mask)
    colors = mag_db[mask]

    fig = plt.figure(figsize=figsize)
    ax = fig.add_subplot(111, projection='3d')

    sc = ax.scatter(
        z_arr[zs] * 100,          # range on x-axis for natural viewing angle
        y_arr[ys] * 100,
        x_arr[xs] * 100,
        c=colors, cmap='hot', vmin=threshold_db, vmax=0,
        s=10, alpha=0.6,
    )
    fig.colorbar(sc, ax=ax, label='dB re peak', shrink=0.5)
    ax.set_xlabel("z / range (cm)")
    ax.set_ylabel("y (cm)")
    ax.set_zlabel("x (cm)")
    ax.set_title(title)
    fig.tight_layout()
    return fig
