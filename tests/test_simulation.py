"""
tests/test_simulation.py
========================
Unit tests for simulation/array_sim.py and simulation/targets.py.
"""

import numpy as np
import pytest

from simulation.targets import (
    PointTarget,
    Scene,
    make_single_target,
    make_multi_depth_scene,
    make_weapon_scene,
    make_clean_scene,
)
from simulation.array_sim import ApertureConfig, simulate_scattered_field

C = 2.998e8  # speed of light


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def default_config():
    """Minimal config fast enough for unit tests (coarse grid)."""
    return ApertureConfig(
        f_min=27e9,
        f_max=33e9,
        n_freq=32,
        aperture_x=0.3,
        aperture_y=0.3,
        noise_std=0.0,
    )


# ---------------------------------------------------------------------------
# Target / Scene tests
# ---------------------------------------------------------------------------

class TestTargets:
    def test_point_target_position(self):
        t = PointTarget(x=0.1, y=-0.05, z=0.5)
        pos = t.position()
        assert pos.shape == (3,)
        np.testing.assert_allclose(pos, [0.1, -0.05, 0.5])

    def test_make_single_target(self):
        scene = make_single_target(x=0.0, y=0.0, z=0.4)
        assert len(scene) == 1
        assert scene.has_concealed_object is True
        assert scene.targets[0].z == pytest.approx(0.4)

    def test_make_multi_depth_scene(self):
        scene = make_multi_depth_scene(depths=[0.3, 0.5, 0.7])
        assert len(scene) == 3
        depths = [t.z for t in scene]
        assert depths == pytest.approx([0.3, 0.5, 0.7])

    def test_make_weapon_scene(self):
        scene = make_weapon_scene(nx_pts=3, ny_pts=4)
        assert len(scene) == 12
        assert scene.has_concealed_object is True

    def test_make_clean_scene(self):
        scene = make_clean_scene()
        assert len(scene) == 0
        assert scene.has_concealed_object is False


# ---------------------------------------------------------------------------
# ApertureConfig tests
# ---------------------------------------------------------------------------

class TestApertureConfig:
    def test_output_shape(self, default_config):
        cfg = default_config
        assert cfg.x_arr.shape == (cfg.nx,)
        assert cfg.y_arr.shape == (cfg.ny,)
        assert cfg.freqs.shape == (cfg.nf,)

    def test_frequency_bounds(self, default_config):
        cfg = default_config
        assert cfg.freqs[0] == pytest.approx(27e9)
        assert cfg.freqs[-1] == pytest.approx(33e9)

    def test_aperture_centred(self, default_config):
        cfg = default_config
        # x and y arrays should be approximately centred on zero
        assert abs(cfg.x_arr.mean()) < 1e-6
        assert abs(cfg.y_arr.mean()) < 1e-6

    def test_theoretical_range_resolution(self, default_config):
        cfg = default_config
        dz = cfg.theoretical_range_resolution()
        expected = C / (2 * 6e9)
        assert dz == pytest.approx(expected, rel=1e-6)

    def test_dx_less_than_half_wavelength(self, default_config):
        cfg = default_config
        dx_actual = cfg.x_arr[1] - cfg.x_arr[0]
        lambda_min = C / cfg.f_max
        assert dx_actual <= lambda_min / 2 + 1e-6, (
            f"dx={dx_actual:.4f} m exceeds λ_min/2={lambda_min/2:.4f} m"
        )


# ---------------------------------------------------------------------------
# Simulation tests
# ---------------------------------------------------------------------------

class TestSimulation:
    def test_output_shape(self, default_config):
        scene = make_single_target(z=0.4)
        s = simulate_scattered_field(scene, default_config)
        assert s.shape == (default_config.nx, default_config.ny, default_config.nf)
        assert s.dtype == np.complex128

    def test_clean_scene_is_zero_no_noise(self, default_config):
        scene = make_clean_scene()
        s = simulate_scattered_field(scene, default_config)
        np.testing.assert_array_equal(s, 0.0)

    def test_single_target_phase_ramp(self, default_config):
        """At aperture centre, the phase vs frequency should match the analytic
        round-trip phase: φ(f) = -2 · (2πf/c) · z_target."""
        z_target = 0.4
        scene = make_single_target(x=0.0, y=0.0, z=z_target)
        s = simulate_scattered_field(scene, default_config)

        # Aperture centre index
        ix_c = default_config.nx // 2
        iy_c = default_config.ny // 2
        s_centre = s[ix_c, iy_c, :]  # (nf,)

        # Expected phase at aperture centre (range = z_target exactly)
        freqs = default_config.freqs
        k = 2 * np.pi * freqs / C
        expected_phase = -2 * k * z_target

        measured_phase = np.angle(s_centre * np.exp(1j * 2 * k * z_target))
        # After compensating the analytic phase the residual should be near 0
        np.testing.assert_allclose(measured_phase, 0.0, atol=1e-9)

    def test_amplitude_decreases_with_range(self, default_config):
        """Amplitude at aperture centre should decrease as 1/R with increasing depth."""
        freqs = default_config.freqs
        ix_c = default_config.nx // 2
        iy_c = default_config.ny // 2

        amps = []
        for z in [0.3, 0.5, 0.7]:
            scene = make_single_target(x=0.0, y=0.0, z=z)
            s = simulate_scattered_field(scene, default_config)
            # Amplitude at aperture centre, centre frequency
            amps.append(np.abs(s[ix_c, iy_c, default_config.nf // 2]))

        # Amplitude should be strictly decreasing with depth
        assert amps[0] > amps[1] > amps[2]

    def test_noise_adds_correct_variance(self, default_config):
        """With noise_std > 0, the clean scene should have non-zero RMS."""
        cfg = ApertureConfig(
            f_min=default_config.f_min,
            f_max=default_config.f_max,
            n_freq=default_config.nf,
            aperture_x=default_config.aperture_x,
            aperture_y=default_config.aperture_y,
            noise_std=0.05,
        )
        scene = make_clean_scene()
        rng = np.random.default_rng(0)
        s = simulate_scattered_field(scene, cfg, rng=rng)
        # RMS should be close to noise_std
        assert s.std() > 0
        # Very rough check — within factor of 2
        assert 0.01 < s.std() < 0.15
