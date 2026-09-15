"""
reconstruction/wideband.py
==========================
Full 3-D wideband holographic reconstruction.

Implements Eq. (23) of Sheen et al. (2001):

    f(x, y, z) = IFFT3D{ FFT2D[s(x, y, ω)] · exp(-j · kz · Z1) }

The algorithm has four steps:

  1. 2-D spatial FFT over (x', y') for every frequency ω:

         S(kx, ky, ω) = FFT2D[ s(x', y', ω) ]

  2. Phase multiply to back-propagate to the reference depth Z1:

         S̃(kx, ky, ω) = S(kx, ky, ω) · exp(-j · kz(kx, ky, ω) · Z1)

     where kz(kx, ky, ω) = sqrt( (2ω/c)² - kx² - ky² ).

     IMPORTANT — why the factor of 2?
     In monostatic (round-trip) operation the effective propagation constant
     is the *two-way* wavenumber 2k = 2ω/c, not the one-way k = ω/c.
     Eq. 22 of the paper writes kz = sqrt(4k² - kx² - ky²) explicitly.

  3. *** kz RESAMPLING (the critical step) ***

     After Step 2 the data S̃(kx, ky, ω) is indexed by frequency ω, but the
     3-D IFFT in Step 4 requires data on a *uniform* (kx, ky, kz) grid.
     The relationship kz = sqrt(4k² - kx² - ky²) is nonlinear in ω (the
     data lives on nested spherical shells in k-space, not a rectangular
     grid), so the kz values are *not* uniformly spaced.

     We fix this by:
       a. For each (kx_m, ky_n) pair, compute the set of nonuniform kz values
          that correspond to the frequency samples ω_0 … ω_{Nf-1}.
       b. Define a uniform kz grid from kz_min to kz_max.
       c. Interpolate S̃[:, :, :] from the nonuniform kz axis onto the uniform
          grid using cubic spline interpolation (scipy.interpolate.interp1d
          with kind='cubic').

     Interpolation choice — cubic vs. linear
     ----------------------------------------
     We use cubic splines rather than linear interpolation.  The scattered
     field is a smooth, band-limited signal in ω (a chirp-like function), so
     cubic splines give significantly better accuracy without any
     Runge-phenomenon risk at the sampling densities we use (N_freq ≥ 64).
     Linear interpolation would introduce a systematic phase error in the
     kz-to-z mapping that degrades depth (range) resolution — the very
     dimension this algorithm is designed to resolve.  This is an intentional,
     physics-motivated choice, not an oversight.

  4. 3-D IFFT over the uniform (kx, ky, kz) grid:

         f(x, y, z) = IFFT3D[ S̃_uniform(kx, ky, kz) ]

     The resulting f[x, y, z] is the 3-D focused reflectivity volume.

References
----------
Sheen, D. M., McMakin, D. L., and Hall, T. E. (2001). Three-dimensional
millimeter-wave imaging for concealed weapon detection. IEEE Transactions on
Microwave Theory and Techniques, 49(9), 1581–1592.
"""

from __future__ import annotations

import numpy as np
from numpy.fft import fft2, ifft2, ifftn, fftfreq, fftshift, ifftshift
from scipy.interpolate import interp1d

C = 2.998e8  # speed of light (m/s)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def reconstruct_wideband(
    s_cube: np.ndarray,
    x_arr: np.ndarray,
    y_arr: np.ndarray,
    freqs: np.ndarray,
    focus_depth: float,
    n_kz: int | None = None,
    verbose: bool = False,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Wideband 3-D holographic reconstruction with kz resampling.

    Parameters
    ----------
    s_cube : ndarray, shape (nx, ny, nf), complex
        Measured scattered field on the aperture × frequency grid.
    x_arr : ndarray, shape (nx,)
        Aperture x-sample positions (m), uniformly spaced.
    y_arr : ndarray, shape (ny,)
        Aperture y-sample positions (m), uniformly spaced.
    freqs : ndarray, shape (nf,)
        Frequency samples (Hz), uniformly spaced.
    focus_depth : float
        Reference depth Z1 (m).  The algorithm focuses across *all* depths
        simultaneously; Z1 is the near-field reference plane used in the
        phase-screen term (paper Section III / Eq. 22).  Typically set to
        the minimum expected target depth.
    n_kz : int, optional
        Number of uniform kz grid points.  If None, uses nf (matches the
        frequency count to avoid interpolation artefacts from over/under-
        sampling in range).
    verbose : bool
        If True, print progress messages.

    Returns
    -------
    f_volume : ndarray, shape (nx, ny, n_kz), complex
        Reconstructed 3-D complex reflectivity volume.
    x_arr : ndarray, shape (nx,)
        x-axis image coordinates (m) — same as input.
    y_arr : ndarray, shape (ny,)
        y-axis image coordinates (m) — same as input.
    z_arr : ndarray, shape (nz,)
        z-axis image coordinates (m) derived from the uniform kz grid.
    """
    nx, ny, nf = s_cube.shape
    if n_kz is None:
        n_kz = nf

    dx = x_arr[1] - x_arr[0]
    dy = y_arr[1] - y_arr[0]

    # -----------------------------------------------------------------------
    # Step 1 — 2-D spatial FFT over aperture for every frequency
    # -----------------------------------------------------------------------
    if verbose:
        print("Step 1: 2-D FFT over aperture...")

    # FFT along axes 0 and 1; retain frequency axis (2) as-is.
    # We use fftshift/ifftshift so that kx=0 and ky=0 land at the array centre
    # — this makes the phase-screen computation straightforward.
    S = fftshift(
        fft2(ifftshift(s_cube, axes=(0, 1)), axes=(0, 1)),
        axes=(0, 1),
    )  # shape (nx, ny, nf)

    # Spatial-frequency axes (rad/m)
    kx = 2 * np.pi * fftshift(fftfreq(nx, d=dx))  # (nx,)
    ky = 2 * np.pi * fftshift(fftfreq(ny, d=dy))  # (ny,)
    KX, KY = np.meshgrid(kx, ky, indexing='ij')   # (nx, ny)

    # Two-way wavenumbers for each frequency
    k_2way = 2 * (2 * np.pi * freqs / C)           # 2 × (ω/c), shape (nf,)

    # -----------------------------------------------------------------------
    # Step 2 — Phase multiply: back-propagate to reference depth Z1
    # -----------------------------------------------------------------------
    if verbose:
        print("Step 2: Phase multiply (back-propagate to Z1={:.3f} m)...".format(focus_depth))

    # kz² = (2k)² - kx² - ky²,  broadcast: (nx, ny, nf)
    # k_2way[np.newaxis, np.newaxis, :] broadcasts to (1, 1, nf)
    kz2 = (k_2way[np.newaxis, np.newaxis, :] ** 2
            - KX[:, :, np.newaxis] ** 2
            - KY[:, :, np.newaxis] ** 2)           # (nx, ny, nf)

    propagating = kz2 >= 0                          # evanescent-mode mask
    kz_all = np.where(propagating, np.sqrt(np.abs(kz2)), 0.0)  # (nx, ny, nf)

    # Phase screen: exp(+j kz Z1), zero out evanescent modes
    # Positive sign back-propagates from aperture to reference depth Z1.
    phase_screen = np.where(propagating, np.exp(+1j * kz_all * focus_depth), 0.0 + 0j)
    S_tilde = S * phase_screen                      # (nx, ny, nf)

    # -----------------------------------------------------------------------
    # Step 3 — kz Resampling onto a uniform grid
    # -----------------------------------------------------------------------
    if verbose:
        print("Step 3: Resampling to uniform kz grid...")

    # The uniform kz grid is determined by the range of kz at the DC
    # spatial-frequency bin (kx=0, ky=0), where kz = 2k and the full
    # frequency sweep is preserved.  At off-axis bins kz covers a smaller
    # range (concentric spheres get clipped), but the interpolator handles
    # out-of-range values by setting them to zero (extrapolation disabled).
    kz_dc_min = k_2way[0]   # kz at kx=ky=0, lowest frequency
    kz_dc_max = k_2way[-1]  # kz at kx=ky=0, highest frequency

    kz_uniform = np.linspace(kz_dc_min, kz_dc_max, n_kz)  # uniform grid

    # Allocate output in (kx, ky, kz) space
    S_uniform = np.zeros((nx, ny, n_kz), dtype=np.complex128)

    # Resample each (kx_m, ky_n) row independently.
    # For each row, kz_all[m, n, :] gives the nf nonuniform kz values (one
    # per frequency); S_tilde[m, n, :] gives the corresponding complex data.
    # scipy interp1d with kind='cubic' fits a cubic spline through these
    # points and evaluates it on kz_uniform.
    for m in range(nx):
        for n in range(ny):
            kz_row = kz_all[m, n, :]               # nonuniform kz values (nf,)
            data_row = S_tilde[m, n, :]             # complex data at those kz

            # Only interpolate if this (kx, ky) bin has propagating modes
            # across at least 2 frequency samples.
            valid = propagating[m, n, :]
            n_valid = np.sum(valid)
            if n_valid < 2:
                continue

            kz_v = kz_row[valid]
            data_v = data_row[valid]

            # Sort by kz (required by interp1d — frequency samples are
            # already monotone in k, so kz is also monotone for fixed kx, ky;
            # but we sort defensively to be safe).
            sort_idx = np.argsort(kz_v)
            kz_v = kz_v[sort_idx]
            data_v = data_v[sort_idx]

            # Deduplicate kz values (can happen at edges of propagating region)
            unique_mask = np.concatenate(([True], np.diff(kz_v) > 0))
            kz_v = kz_v[unique_mask]
            data_v = data_v[unique_mask]

            if len(kz_v) < 4:
                # Fall back to linear if too few points for cubic
                kind = 'linear'
            else:
                kind = 'cubic'

            # Real and imaginary parts interpolated separately (scipy interp1d
            # does not natively support complex data).
            f_re = interp1d(kz_v, data_v.real, kind=kind,
                            bounds_error=False, fill_value=0.0)
            f_im = interp1d(kz_v, data_v.imag, kind=kind,
                            bounds_error=False, fill_value=0.0)

            S_uniform[m, n, :] = f_re(kz_uniform) + 1j * f_im(kz_uniform)

    # -----------------------------------------------------------------------
    # Step 4 — 3-D IFFT to obtain the focused reflectivity volume
    # -----------------------------------------------------------------------
    if verbose:
        print("Step 4: 3-D IFFT...")

    # S_uniform has centred (kx, ky) axes (fftshifted) and monotonic kz from
    # min to max. We apply ifftshift on axes (0, 1) only, perform ifftn across
    # all three axes, and fftshift axes (0, 1) back to centre (x, y).
    f_volume = fftshift(
        ifftn(ifftshift(S_uniform, axes=(0, 1)), axes=(0, 1, 2)),
        axes=(0, 1),
    )  # shape (nx, ny, n_kz)

    # Reconstruct the z-axis coordinates corresponding to the uniform kz grid.
    # IFFT of a signal spanning [kz_min, kz_max] with N_kz points has a
    # spatial period T_z = 2π / Δkz and sample spacing δz = T_z / N_kz.
    # Since phase multiplication focused to reference depth Z1, the z grid
    # is offset by focus_depth.
    dkz = kz_uniform[1] - kz_uniform[0]
    dz = 2 * np.pi / (n_kz * dkz)
    z_arr = np.arange(n_kz) * dz + focus_depth

    if verbose:
        print("Reconstruction complete.  Volume shape: {}".format(f_volume.shape))
        print("z range: [{:.3f}, {:.3f}] m  (δz = {:.4f} m)".format(
            z_arr[0], z_arr[-1], dz))

    return f_volume, x_arr, y_arr, z_arr


# ---------------------------------------------------------------------------
# Convenience: theoretical resolution bounds
# ---------------------------------------------------------------------------

def theoretical_range_resolution(f_min: float, f_max: float) -> float:
    """Range resolution from paper Eq. (29): δz ≈ c / (2B).

    Parameters
    ----------
    f_min, f_max : float
        Frequency sweep bounds (Hz).
    """
    B = f_max - f_min
    return C / (2 * B)


def theoretical_cross_range_resolution(
    f_center: float, range_depth: float, aperture: float
) -> float:
    """Cross-range resolution from paper Eq. (27)/(28): δx ≈ λ R / D.

    Parameters
    ----------
    f_center : float
        Centre frequency (Hz).
    range_depth : float
        Target depth z (m).
    aperture : float
        Aperture size D (m) in one cross-range dimension.
    """
    wavelength = C / f_center
    return wavelength * range_depth / aperture
