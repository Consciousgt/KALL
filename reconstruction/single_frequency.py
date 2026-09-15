"""
reconstruction/single_frequency.py
===================================
Narrow-band backward-wave holographic reconstruction for a single frequency.

Implements Eq. (11) of Sheen et al. (2001):

    f(x, y) = IFFT2D[ FFT2D[s(x', y')] · exp(-j · kz · Z1) ]

where:
    kz = sqrt(4k² - kx² - ky²)    (propagation constant perpendicular to aperture)
    k  = ω / c = 2π f / c         (wavenumber)
    Z1 = target depth (m) from aperture plane

Physical interpretation
-----------------------
The 2-D FFT decomposes the measured aperture field into plane-wave components
(kx, ky).  The complex exponential is a matched phase-correction that
back-propagates each plane-wave component to the focal depth Z1.  The IFFT
then synthesises the focused image at that depth.

Evanescent modes — for which kx² + ky² > 4k² — are set to zero (they carry
no propagating energy from the target plane to the aperture).

Limitation: this reconstruction is focused at a *single* range depth Z1.
Targets at depths other than Z1 will appear blurred.  This motivates the
wideband 3-D algorithm in `wideband.py`.
"""

from __future__ import annotations

import numpy as np
from numpy.fft import fft2, ifft2, fftfreq, fftshift, ifftshift

C = 2.998e8  # speed of light (m/s)


def reconstruct_single_frequency(
    s: np.ndarray,
    x_arr: np.ndarray,
    y_arr: np.ndarray,
    freq: float,
    focus_depth: float,
) -> np.ndarray:
    """Narrow-band backward-wave reconstruction at a single frequency.

    Parameters
    ----------
    s : ndarray, shape (nx, ny), complex
        Measured aperture data at *one* frequency.  If a 3-D array of shape
        (nx, ny, nf) is passed, the slice at `freq` must be extracted before
        calling (or use `reconstruct_single_frequency_from_cube`).
    x_arr : ndarray, shape (nx,)
        Aperture x-sample positions (m), uniformly spaced.
    y_arr : ndarray, shape (ny,)
        Aperture y-sample positions (m), uniformly spaced.
    freq : float
        Frequency of this data slice (Hz).
    focus_depth : float
        Range depth Z1 (m) at which to focus the reconstruction.

    Returns
    -------
    f_image : ndarray, shape (nx, ny), complex
        Reconstructed complex image at depth Z1.
        Take |f_image| for the magnitude (reflectivity amplitude) image.

    Notes
    -----
    Spatial-frequency axes are computed from the aperture sample spacings via
    the FFT frequency formula.  The result is ifftshifted so that the image
    is spatially aligned with the input x_arr, y_arr coordinate grid.
    """
    nx, ny = s.shape[:2]
    dx = x_arr[1] - x_arr[0]  # aperture sample spacing (m)
    dy = y_arr[1] - y_arr[0]

    # Wavenumber at this frequency
    k = 2 * np.pi * freq / C

    # --- Step 1: 2-D FFT of the aperture field ---
    # fftshift / ifftshift ensures DC is at (kx=0, ky=0) for the filter step.
    S = fftshift(fft2(ifftshift(s, axes=(0, 1)), axes=(0, 1)), axes=(0, 1))

    # --- Spatial-frequency axes ---
    kx = 2 * np.pi * fftshift(fftfreq(nx, d=dx))  # (nx,)
    ky = 2 * np.pi * fftshift(fftfreq(ny, d=dy))  # (ny,)
    KX, KY = np.meshgrid(kx, ky, indexing='ij')   # (nx, ny)

    # --- Step 2: Propagation constant kz (Eq. 11) ---
    kz2 = 4 * k ** 2 - KX ** 2 - KY ** 2
    propagating = kz2 >= 0                         # mask: suppress evanescent modes
    kz = np.where(propagating, np.sqrt(np.abs(kz2)), 0.0)

    # --- Step 3: Matched phase-screen (back-propagation to depth Z1) ---
    #
    # The forward model gives: S(kx,ky) = F(kx,ky) · exp(−j·kz·z₁)
    # Inverting requires: F = S · exp(+j·kz·z₁)   ← positive sign
    #
    # Using exp(−j·kz·z₁) (forward propagation) does NOT focus the image;
    # it propagates the field further away from the aperture.  This is the
    # single most common sign error in SAR/holographic reconstruction code.
    H = np.where(propagating, np.exp(+1j * kz * focus_depth), 0.0)

    # --- Step 4: Apply filter and IFFT back to spatial domain ---
    f_image = fftshift(ifft2(ifftshift(S * H, axes=(0, 1)), axes=(0, 1)), axes=(0, 1))

    return f_image


def reconstruct_single_frequency_from_cube(
    s_cube: np.ndarray,
    x_arr: np.ndarray,
    y_arr: np.ndarray,
    freqs: np.ndarray,
    focus_depth: float,
    freq_index: int | None = None,
) -> np.ndarray:
    """Convenience wrapper: extract one frequency slice from a 3-D cube and reconstruct.

    Parameters
    ----------
    s_cube : ndarray, shape (nx, ny, nf)
        Full scattered-field data cube.
    freqs : ndarray, shape (nf,)
        Frequency array (Hz) corresponding to the third axis of s_cube.
    focus_depth : float
        Range depth Z1 (m) at which to focus.
    freq_index : int, optional
        Index into `freqs` to use.  If None, uses the centre frequency index.

    Returns
    -------
    f_image : ndarray, shape (nx, ny), complex
    """
    if freq_index is None:
        freq_index = len(freqs) // 2
    s_slice = s_cube[:, :, freq_index]
    return reconstruct_single_frequency(
        s_slice, x_arr, y_arr, freqs[freq_index], focus_depth
    )
