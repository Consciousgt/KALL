"""
simulation/array_sim.py
=======================
Simulates the 2-D planar-scan monostatic SAR measurement for a collection
of point scatterers.

Physical model
--------------
The measurement geometry follows Sheen et al. (2001), Section II:

  - A planar aperture at z = 0 is raster-scanned in (x', y').
  - A wideband monostatic transceiver at (x', y', 0) transmits and receives
    at each position across a swept frequency band [f_min, f_max].
  - Targets are at positions (x_i, y_i, z_i) with z_i > 0.

For a set of point targets the round-trip scattered field is (Eq. 13):

    s(x', y', ω) = Σ_i  A_i · exp(-j 2 k R_i)

where:
    k  = ω / c  =  2π f / c     (wavenumber)
    R_i = sqrt((x_i-x')² + (y_i-y')² + z_i²)

Note: the paper writes the range relative to the focus plane Z1; in our
coordinate system Z1 ≡ z_i (the target's actual depth), which collapses
the integral to a simple closed-form sum for point scatterers.

Nyquist criterion (paper Eq. 24): Δx < λ_min / 4, relaxed to λ_min / 2
in practice.

Outputs
-------
s : ndarray, shape (Nx, Ny, Nf), complex128
    Simulated scattered field on the (x, y) aperture grid for each
    frequency sample.  Axes are [x-aperture, y-aperture, frequency].

Related coordinate grids (returned in SystemConfig):
    x_arr, y_arr : 1-D aperture sample positions (m)
    freqs        : 1-D frequency array (Hz)
"""

from __future__ import annotations

import dataclasses
import numpy as np
from typing import Sequence

from .targets import Scene

# Speed of light (m/s)
C = 2.998e8


# ---------------------------------------------------------------------------
# System / aperture configuration
# ---------------------------------------------------------------------------

@dataclasses.dataclass
class ApertureConfig:
    """Complete description of the scan aperture and frequency sweep.

    Parameters
    ----------
    f_min, f_max : float
        Frequency sweep bounds (Hz).  Default: 27–33 GHz (K-band, B=6 GHz).
    n_freq : int
        Number of frequency samples across [f_min, f_max].
    aperture_x, aperture_y : float
        Physical aperture extent (m).  Default: 0.5 m × 0.5 m.
    dx, dy : float or None
        Spatial sampling step (m).  If None, computed automatically as
        λ_min / 2 (Nyquist criterion, paper Eq. 24, relaxed factor).
    noise_std : float
        Standard deviation of additive complex Gaussian noise added to the
        simulated data.  Set to 0 for noise-free simulation.
    """
    f_min: float = 27e9          # Hz
    f_max: float = 33e9          # Hz
    n_freq: int = 128
    aperture_x: float = 0.5      # m
    aperture_y: float = 0.5      # m
    dx: float | None = None      # m; auto-computed if None
    dy: float | None = None      # m; auto-computed if None
    noise_std: float = 0.0

    # --- derived quantities (populated by __post_init__) ---
    _x_arr: np.ndarray = dataclasses.field(init=False, repr=False)
    _y_arr: np.ndarray = dataclasses.field(init=False, repr=False)
    _freqs: np.ndarray = dataclasses.field(init=False, repr=False)

    def __post_init__(self) -> None:
        lambda_min = C / self.f_max

        dx = self.dx if self.dx is not None else lambda_min / 2
        dy = self.dy if self.dy is not None else lambda_min / 2

        # Aperture sample positions (centred on 0)
        nx = max(int(np.ceil(self.aperture_x / dx)), 2)
        ny = max(int(np.ceil(self.aperture_y / dy)), 2)
        # Force odd length so DC bin is centred
        if nx % 2 == 0:
            nx += 1
        if ny % 2 == 0:
            ny += 1

        self._x_arr = np.linspace(-self.aperture_x / 2, self.aperture_x / 2, nx)
        self._y_arr = np.linspace(-self.aperture_y / 2, self.aperture_y / 2, ny)
        self._freqs = np.linspace(self.f_min, self.f_max, self.n_freq)

    # --- public read-only accessors ---

    @property
    def x_arr(self) -> np.ndarray:
        """Aperture x-sample positions (m)."""
        return self._x_arr

    @property
    def y_arr(self) -> np.ndarray:
        """Aperture y-sample positions (m)."""
        return self._y_arr

    @property
    def freqs(self) -> np.ndarray:
        """Frequency samples (Hz)."""
        return self._freqs

    @property
    def nx(self) -> int:
        return len(self._x_arr)

    @property
    def ny(self) -> int:
        return len(self._y_arr)

    @property
    def nf(self) -> int:
        return len(self._freqs)

    @property
    def bandwidth(self) -> float:
        """One-sided bandwidth B = f_max - f_min (Hz)."""
        return self.f_max - self.f_min

    @property
    def f_center(self) -> float:
        return (self.f_min + self.f_max) / 2

    @property
    def lambda_center(self) -> float:
        """Free-space wavelength at the centre frequency (m)."""
        return C / self.f_center

    def theoretical_range_resolution(self) -> float:
        """Range (depth) resolution from paper Eq. (29): δz ≈ c / (2B)."""
        return C / (2 * self.bandwidth)

    def theoretical_cross_range_resolution(self, range_depth: float) -> float:
        """Cross-range resolution from paper Eq. (27)/(28): δx ≈ λ·R / D.

        Parameters
        ----------
        range_depth : float
            Target depth z (m) from the aperture plane.
        """
        return self.lambda_center * range_depth / self.aperture_x


# ---------------------------------------------------------------------------
# Core simulation function
# ---------------------------------------------------------------------------

def simulate_scattered_field(
    scene: Scene,
    config: ApertureConfig,
    rng: np.random.Generator | None = None,
) -> np.ndarray:
    """Simulate the 2-D planar-scan scattered field for a scene of point targets.

    Computes:

        s[ix, iy, iω] = Σ_i  A_i · exp(-j 2 k R_i(ix, iy))

    where R_i is the range from transceiver position (x', y', 0) to target i
    at (x_i, y_i, z_i).

    Parameters
    ----------
    scene : Scene
        Collection of PointTargets defining the scene.
    config : ApertureConfig
        Aperture geometry and frequency sweep parameters.
    rng : numpy Generator, optional
        Random generator for additive noise (reproducible results).

    Returns
    -------
    s : ndarray, shape (nx, ny, nf), complex128
        Simulated scattered field.  Empty scene returns all-zeros array.
    """
    nx, ny, nf = config.nx, config.ny, config.nf
    s = np.zeros((nx, ny, nf), dtype=np.complex128)

    if len(scene) == 0:
        # Clean scene — add noise only
        if config.noise_std > 0:
            if rng is None:
                rng = np.random.default_rng()
            noise = rng.standard_normal((nx, ny, nf)) + 1j * rng.standard_normal((nx, ny, nf))
            s += config.noise_std / np.sqrt(2) * noise
        return s

    # Precompute wavenumbers k = 2π f / c, shape (nf,)
    k = 2 * np.pi * config.freqs / C  # (nf,)

    # Aperture meshgrid, shapes (nx, ny)
    xx, yy = np.meshgrid(config.x_arr, config.y_arr, indexing='ij')  # (nx, ny)

    for target in scene:
        xi, yi, zi = target.x, target.y, target.z
        Ai = target.amplitude

        # Range from each aperture position to this target, shape (nx, ny)
        R = np.sqrt((xi - xx) ** 2 + (yi - yy) ** 2 + zi ** 2)

        # Round-trip phase: exp(-j 2 k R), broadcast over frequencies
        # R: (nx, ny, 1),  k: (1, 1, nf)
        phase = np.exp(-1j * 2 * k[np.newaxis, np.newaxis, :] * R[:, :, np.newaxis])
        s += Ai * phase

    # Additive complex Gaussian noise
    if config.noise_std > 0:
        if rng is None:
            rng = np.random.default_rng()
        noise = rng.standard_normal((nx, ny, nf)) + 1j * rng.standard_normal((nx, ny, nf))
        s += config.noise_std / np.sqrt(2) * noise

    return s
