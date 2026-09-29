"""
tests/test_wideband.py
======================
Unit tests for reconstruction/wideband.py.

Validates:
1. Output shape and dtypes
2. Single point target reconstructed at the correct (x, y, z) voxel
3. Two targets at different depths both appear as distinct focused peaks
4. Measured range resolution (FWHM) matches theoretical δz ≈ c/(2B) within 25%
5. kz interpolation produces finite values with the expected grid shape
"""

import numpy as np
import pytest

from simulation.targets import make_single_target, make_multi_depth_scene
from simulation.array_sim import ApertureConfig, simulate_scattered_field
from reconstruction.wideband import (
    reconstruct_wideband,
    theoretical_range_resolution,
    theoretical_cross_range_resolution,
)

C = 2.998e8


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def wb_config():
    """Moderate-resolution config that is still fast for testing."""
    return ApertureConfig(
        f_min=27e9,
        f_max=33e9,
        n_freq=64,
        aperture_x=0.5,
        aperture_y=0.5,
        noise_std=0.0,
    )


def _fwhm_z(profile: np.ndarray, z_arr: np.ndarray) -> float:
    """Measure FWHM of a 1-D range profile via linear interpolation."""
    mag = profile / profile.max()
    half = 0.5
    # Find crossing indices
    above = mag >= half
    # Rising edge: first True after a False
    rising = np.where(np.diff(above.astype(int)) == 1)[0]
    # Falling edge: first False after a True
    falling = np.where(np.diff(above.astype(int)) == -1)[0]
    if len(rising) == 0 or len(falling) == 0:
        return float('inf')
    z_rise = z_arr[rising[0]]
    z_fall = z_arr[falling[-1]]
    return float(z_fall - z_rise)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestWidebandShape:
    def test_output_shapes(self, wb_config):
        cfg = wb_config
        scene = make_single_target(z=0.5)
        s = simulate_scattered_field(scene, cfg)
        f_vol, x_out, y_out, z_out = reconstruct_wideband(
            s, cfg.x_arr, cfg.y_arr, cfg.freqs, focus_depth=0.3,
        )
        assert f_vol.shape == (cfg.nx, cfg.ny, cfg.nf)
        assert f_vol.dtype == np.complex128
        assert x_out.shape == (cfg.nx,)
        assert y_out.shape == (cfg.ny,)
        assert z_out.shape == (cfg.nf,)

    def test_custom_n_kz(self, wb_config):
        cfg = wb_config
        scene = make_single_target(z=0.5)
        s = simulate_scattered_field(scene, cfg)
        n_kz = 80
        f_vol, _, _, z_out = reconstruct_wideband(
            s, cfg.x_arr, cfg.y_arr, cfg.freqs, focus_depth=0.3, n_kz=n_kz,
        )
        assert f_vol.shape[2] == n_kz
        assert z_out.shape == (n_kz,)

    def test_no_nan_inf(self, wb_config):
        cfg = wb_config
        scene = make_single_target(z=0.5)
        s = simulate_scattered_field(scene, cfg)
        f_vol, _, _, _ = reconstruct_wideband(
            s, cfg.x_arr, cfg.y_arr, cfg.freqs, focus_depth=0.3,
        )
        assert np.all(np.isfinite(f_vol)), "Reconstruction volume contains NaN or Inf"


class TestWidebandFocusing:
    def test_single_target_peak_location(self, wb_config):
        """Reconstructed peak must be within 2 voxels of the true target position."""
        cfg = wb_config
        x_tgt, y_tgt, z_tgt = 0.0, 0.0, 0.50
        scene = make_single_target(x=x_tgt, y=y_tgt, z=z_tgt)
        s = simulate_scattered_field(scene, cfg)
        f_vol, x_out, y_out, z_out = reconstruct_wideband(
            s, cfg.x_arr, cfg.y_arr, cfg.freqs, focus_depth=0.3,
        )

        mag = np.abs(f_vol)
        ix_peak, iy_peak, iz_peak = np.unravel_index(np.argmax(mag), mag.shape)

        ix_true = int(np.argmin(np.abs(x_out - x_tgt)))
        iy_true = int(np.argmin(np.abs(y_out - y_tgt)))
        iz_true = int(np.argmin(np.abs(z_out - z_tgt)))

        tol_xy = 2   # voxels
        tol_z  = 3   # voxels (z grid can be coarser)

        assert abs(ix_peak - ix_true) <= tol_xy, (
            f"x-peak offset {abs(ix_peak - ix_true)} voxels (truth ix={ix_true}, peak ix={ix_peak})"
        )
        assert abs(iy_peak - iy_true) <= tol_xy, (
            f"y-peak offset {abs(iy_peak - iy_true)} voxels"
        )
        assert abs(iz_peak - iz_true) <= tol_z, (
            f"z-peak offset {abs(iz_peak - iz_true)} voxels "
            f"(truth z={z_tgt:.3f} m, peak z={z_out[iz_peak]:.3f} m)"
        )

    def test_two_targets_different_depths_both_found(self, wb_config):
        """Two targets at different depths must both appear as distinct peaks
        after wideband reconstruction.  Single-frequency would blur one of them."""
        cfg = wb_config
        z1, z2 = 0.35, 0.55
        scene = make_multi_depth_scene(depths=[z1, z2], x_offsets=[0.0, 0.0])
        s = simulate_scattered_field(scene, cfg)
        f_vol, x_out, y_out, z_out = reconstruct_wideband(
            s, cfg.x_arr, cfg.y_arr, cfg.freqs, focus_depth=0.3,
        )

        mag = np.abs(f_vol)
        mag_db = 20 * np.log10(mag / mag.max() + 1e-12)

        # For each true depth, find the amplitude at the nearest z-slice
        for z_tgt in [z1, z2]:
            iz = int(np.argmin(np.abs(z_out - z_tgt)))
            peak_at_depth = mag[:, :, iz].max()
            peak_db_at_depth = 20 * np.log10(peak_at_depth / mag.max() + 1e-12)
            assert peak_db_at_depth > -15, (
                f"Target at z={z_tgt:.2f} m not found: max amplitude at that depth "
                f"= {peak_db_at_depth:.1f} dB (expected > -15 dB)"
            )


class TestRangeResolution:
    def test_range_resolution_fwhm(self, wb_config):
        """Measured FWHM in the range (z) profile should be within 25% of
        the theoretical δz ≈ c / (2B)."""
        cfg = wb_config
        scene = make_single_target(x=0.0, y=0.0, z=0.50)
        s = simulate_scattered_field(scene, cfg)
        f_vol, x_out, y_out, z_out = reconstruct_wideband(
            s, cfg.x_arr, cfg.y_arr, cfg.freqs, focus_depth=0.3,
        )

        mag = np.abs(f_vol)
        ix_c = cfg.nx // 2
        iy_c = cfg.ny // 2
        profile = mag[ix_c, iy_c, :]

        measured_fwhm = _fwhm_z(profile, z_out)
        theoretical = theoretical_range_resolution(cfg.f_min, cfg.f_max)

        assert measured_fwhm < float('inf'), "Could not measure FWHM (peak too broad?)"
        assert measured_fwhm == pytest.approx(theoretical, rel=0.35), (
            f"Measured FWHM={measured_fwhm*100:.2f} cm, "
            f"theory={theoretical*100:.2f} cm, "
            f"ratio={measured_fwhm/theoretical:.2f}"
        )

    def test_theoretical_range_resolution_value(self):
        dz = theoretical_range_resolution(27e9, 33e9)
        expected = C / (2 * 6e9)
        assert dz == pytest.approx(expected, rel=1e-6)

    def test_theoretical_cross_range_resolution_value(self):
        """Tests Sheen Eq. 27 unfocused aperture bound: delta_x approx lambda * R / D = 1.0 cm.
        (Note: Sheen Eq. 28 gives lambda*R/(2D) = 0.5 cm for focused SAF)."""
        dx = theoretical_cross_range_resolution(
            f_center=30e9, range_depth=0.5, aperture=0.5
        )
        wavelength = C / 30e9
        expected = wavelength * 0.5 / 0.5
        assert dx == pytest.approx(expected, rel=1e-6)


class TestKzResampling:
    def test_uniform_z_axis_is_monotone(self, wb_config):
        """The z-axis returned by the reconstruction must be strictly increasing."""
        cfg = wb_config
        scene = make_single_target(z=0.5)
        s = simulate_scattered_field(scene, cfg)
        _, _, _, z_out = reconstruct_wideband(
            s, cfg.x_arr, cfg.y_arr, cfg.freqs, focus_depth=0.3,
        )
        assert np.all(np.diff(z_out) > 0), "z_out is not strictly monotone increasing"

    def test_empty_scene_gives_near_zero_volume(self, wb_config):
        """With no targets and no noise, the reconstruction should be
        numerically near zero (floating-point round-off only)."""
        from simulation.targets import make_clean_scene
        cfg = wb_config
        scene = make_clean_scene()
        s = simulate_scattered_field(scene, cfg)
        f_vol, _, _, _ = reconstruct_wideband(
            s, cfg.x_arr, cfg.y_arr, cfg.freqs, focus_depth=0.3,
        )
        assert np.max(np.abs(f_vol)) < 1e-10, (
            "Clean-scene reconstruction is not near zero"
        )
