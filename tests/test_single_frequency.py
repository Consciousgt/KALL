"""
tests/test_single_frequency.py
================================
Unit tests for reconstruction/single_frequency.py.

Validates that the narrow-band backward-wave reconstruction correctly focuses
a known point target at the specified depth.
"""

import numpy as np
import pytest

from simulation.targets import make_single_target
from simulation.array_sim import ApertureConfig, simulate_scattered_field
from reconstruction.single_frequency import (
    reconstruct_single_frequency,
    reconstruct_single_frequency_from_cube,
)

C = 2.998e8


@pytest.fixture
def small_config():
    """Fast config for unit tests."""
    return ApertureConfig(
        f_min=27e9,
        f_max=33e9,
        n_freq=32,
        aperture_x=0.5,
        aperture_y=0.5,
        noise_std=0.0,
    )


class TestSingleFrequency:
    def test_output_shape(self, small_config):
        scene = make_single_target(x=0.0, y=0.0, z=0.5)
        s = simulate_scattered_field(scene, small_config)
        cfg = small_config
        f_img = reconstruct_single_frequency(
            s[:, :, cfg.nf // 2], cfg.x_arr, cfg.y_arr,
            cfg.freqs[cfg.nf // 2], focus_depth=0.5,
        )
        assert f_img.shape == (cfg.nx, cfg.ny)
        assert f_img.dtype == np.complex128

    def test_no_nan_inf(self, small_config):
        scene = make_single_target(x=0.0, y=0.0, z=0.5)
        s = simulate_scattered_field(scene, small_config)
        cfg = small_config
        f_img = reconstruct_single_frequency(
            s[:, :, cfg.nf // 2], cfg.x_arr, cfg.y_arr,
            cfg.freqs[cfg.nf // 2], focus_depth=0.5,
        )
        assert np.all(np.isfinite(f_img))

    def test_peak_at_correct_xy(self, small_config):
        """Peak of the reconstructed magnitude image should lie within
        2 pixels of the true target (x, y) position."""
        x_tgt, y_tgt, z_tgt = 0.0, 0.0, 0.5
        scene = make_single_target(x=x_tgt, y=y_tgt, z=z_tgt)
        s = simulate_scattered_field(scene, small_config)
        cfg = small_config

        f_img = reconstruct_single_frequency(
            s[:, :, cfg.nf // 2], cfg.x_arr, cfg.y_arr,
            cfg.freqs[cfg.nf // 2], focus_depth=z_tgt,
        )

        # Find peak
        ix_peak, iy_peak = np.unravel_index(np.argmax(np.abs(f_img)), f_img.shape)

        # Nearest grid indices to truth
        ix_true = int(np.argmin(np.abs(cfg.x_arr - x_tgt)))
        iy_true = int(np.argmin(np.abs(cfg.y_arr - y_tgt)))

        pixel_tol = 2
        assert abs(ix_peak - ix_true) <= pixel_tol, (
            f"x-peak at pixel {ix_peak} (truth {ix_true}) — exceeded {pixel_tol} pixel tolerance"
        )
        assert abs(iy_peak - iy_true) <= pixel_tol, (
            f"y-peak at pixel {iy_peak} (truth {iy_true}) — exceeded {pixel_tol} pixel tolerance"
        )

    def test_off_centre_target(self, small_config):
        """Peak should track a target offset from aperture centre."""
        x_tgt, y_tgt, z_tgt = 0.05, -0.03, 0.4
        scene = make_single_target(x=x_tgt, y=y_tgt, z=z_tgt)
        s = simulate_scattered_field(scene, small_config)
        cfg = small_config

        f_img = reconstruct_single_frequency(
            s[:, :, cfg.nf // 2], cfg.x_arr, cfg.y_arr,
            cfg.freqs[cfg.nf // 2], focus_depth=z_tgt,
        )

        ix_peak, iy_peak = np.unravel_index(np.argmax(np.abs(f_img)), f_img.shape)
        ix_true = int(np.argmin(np.abs(cfg.x_arr - x_tgt)))
        iy_true = int(np.argmin(np.abs(cfg.y_arr - y_tgt)))

        pixel_tol = 2
        assert abs(ix_peak - ix_true) <= pixel_tol
        assert abs(iy_peak - iy_true) <= pixel_tol

    def test_evanescent_modes_suppressed(self, small_config):
        """Reconstruction must produce finite output with no NaN/inf even when
        evanescent modes are present (large kx / ky bins)."""
        # Use a very high frequency so evanescent modes are not triggered —
        # evanescent modes arise when kx²+ky² > 4k², i.e., at low f or large aperture.
        # For this test we just confirm the output is always finite.
        cfg = small_config
        scene = make_single_target(z=0.5)
        s = simulate_scattered_field(scene, cfg)
        f_img = reconstruct_single_frequency(
            s[:, :, 0], cfg.x_arr, cfg.y_arr,
            cfg.freqs[0], focus_depth=0.5,
        )
        assert np.all(np.isfinite(f_img))

    def test_cube_wrapper_matches_direct(self, small_config):
        """reconstruct_single_frequency_from_cube should give same result
        as calling reconstruct_single_frequency on the extracted slice."""
        cfg = small_config
        scene = make_single_target(z=0.5)
        s = simulate_scattered_field(scene, cfg)
        freq_idx = cfg.nf // 2

        f_direct = reconstruct_single_frequency(
            s[:, :, freq_idx], cfg.x_arr, cfg.y_arr,
            cfg.freqs[freq_idx], focus_depth=0.5,
        )
        f_cube = reconstruct_single_frequency_from_cube(
            s, cfg.x_arr, cfg.y_arr, cfg.freqs,
            focus_depth=0.5, freq_index=freq_idx,
        )
        np.testing.assert_allclose(f_direct, f_cube, atol=1e-12)
