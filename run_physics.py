"""
run_physics.py
==============
End-to-end demonstration of the physics reconstruction pipeline.

Runs the simulation → single-frequency → wideband reconstruction for a
multi-depth target scene, saves four output figures to results/, and prints
resolution measurements vs theory.

Usage:
    python run_physics.py
"""

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path

from simulation.targets import make_multi_depth_scene, make_single_target
from simulation.array_sim import ApertureConfig, simulate_scattered_field
from reconstruction.single_frequency import reconstruct_single_frequency_from_cube
from reconstruction.wideband import (
    reconstruct_wideband,
    theoretical_range_resolution,
    theoretical_cross_range_resolution,
)
from visualization.plots import (
    plot_mip,
    plot_comparison_mip,
    plot_range_profile,
    plot_3d_scatter,
)

RESULTS_DIR = Path(__file__).parent / "results"
RESULTS_DIR.mkdir(exist_ok=True)

C = 2.998e8

# -----------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------
cfg = ApertureConfig(
    f_min=27e9,
    f_max=33e9,
    n_freq=128,
    aperture_x=0.5,
    aperture_y=0.5,
    noise_std=0.01,
)

print("=" * 60)
print("mmwave-imaging — Physics reconstruction demo")
print("=" * 60)
print(f"  Frequency:    {cfg.f_min/1e9:.0f}–{cfg.f_max/1e9:.0f} GHz  (B = {cfg.bandwidth/1e9:.0f} GHz)")
print(f"  Aperture:     {cfg.aperture_x*100:.0f} cm × {cfg.aperture_y*100:.0f} cm")
print(f"  Grid:         {cfg.nx} × {cfg.ny} × {cfg.nf}")
print(f"  λ_min / 2:    {(C/cfg.f_max)/2*1000:.1f} mm  (dx = {(cfg.x_arr[1]-cfg.x_arr[0])*1000:.1f} mm)")
print(f"  δz theory:    {theoretical_range_resolution(cfg.f_min, cfg.f_max)*100:.2f} cm")
print(f"  δx theory:    {theoretical_cross_range_resolution(cfg.f_center, 0.5, cfg.aperture_x)*10:.1f} mm (at z=50 cm)")
print()

# -----------------------------------------------------------------------
# Scene: three point targets at different depths
# -----------------------------------------------------------------------
scene = make_multi_depth_scene(
    depths=[0.35, 0.50, 0.65],
    x_offsets=[ 0.05, -0.03,  0.08],
    y_offsets=[-0.04,  0.06, -0.02],
)
print(f"Scene: {len(scene)} point targets at z = 0.35 m, 0.50 m, 0.65 m")
print("Simulating scattered field...")
s = simulate_scattered_field(scene, cfg)
print(f"  s.shape = {s.shape}  ({s.nbytes/1e6:.1f} MB)")
print()

# -----------------------------------------------------------------------
# Single-frequency reconstruction (centre frequency)
# -----------------------------------------------------------------------
print("Running single-frequency reconstruction...")
focus_depth = 0.50  # focus at the middle target
f_sf = reconstruct_single_frequency_from_cube(
    s, cfg.x_arr, cfg.y_arr, cfg.freqs, focus_depth=focus_depth,
)
print(f"  f_sf.shape = {f_sf.shape}")

# -----------------------------------------------------------------------
# Wideband reconstruction
# -----------------------------------------------------------------------
print("Running wideband reconstruction (this may take ~30 s on CPU)...")
f_vol, x_out, y_out, z_out = reconstruct_wideband(
    s, cfg.x_arr, cfg.y_arr, cfg.freqs, focus_depth=0.25, verbose=True,
)
print(f"  f_vol.shape = {f_vol.shape}")
print(f"  z range: [{z_out[0]*100:.1f}, {z_out[-1]*100:.1f}] cm")
print()

# -----------------------------------------------------------------------
# Resolution measurement
# -----------------------------------------------------------------------
# Use the single central target scene for clean FWHM measurement
print("Measuring range resolution (single on-axis target)...")
cfg_single = ApertureConfig(f_min=27e9, f_max=33e9, n_freq=128,
                             aperture_x=0.5, aperture_y=0.5, noise_std=0.0)
scene_single = make_single_target(x=0.0, y=0.0, z=0.50)
s_single = simulate_scattered_field(scene_single, cfg_single)
fv, _, _, zv = reconstruct_wideband(
    s_single, cfg_single.x_arr, cfg_single.y_arr, cfg_single.freqs,
    focus_depth=0.25,
)
ix_c = cfg_single.nx // 2
iy_c = cfg_single.ny // 2
profile = np.abs(fv[ix_c, iy_c, :])
prof_max = profile.max()
if prof_max > 0:
    profile_norm = profile / prof_max
    above_half = profile_norm >= 0.5
    rising  = np.where(np.diff(above_half.astype(int)) ==  1)[0]
    falling = np.where(np.diff(above_half.astype(int)) == -1)[0]
    if len(rising) > 0 and len(falling) > 0:
        fwhm = zv[falling[-1]] - zv[rising[0]]
        theory = theoretical_range_resolution(27e9, 33e9)
        print(f"  Measured FWHM:  {fwhm*100:.2f} cm")
        print(f"  Theory δz:      {theory*100:.2f} cm")
        print(f"  Ratio:          {fwhm/theory:.2f}  (ideal = 1.0)")
    else:
        print("  FWHM measurement: peak not resolved (adjust depth/grid)")
print()

# -----------------------------------------------------------------------
# Save figures
# -----------------------------------------------------------------------
print("Saving figures to results/...")

# 1. Comparison MIP: single-freq vs wideband
fig = plot_comparison_mip(
    vol_sf=f_sf,
    vol_wb=f_vol,
    x_arr=x_out, y_arr=y_out,
    suptitle="Single-frequency vs Wideband Reconstruction\n(3 point targets at 35, 50, 65 cm depth)",
)
fig.savefig(RESULTS_DIR / "comparison_mip.png", dpi=150, bbox_inches='tight')
plt.close(fig)

# 2. Wideband MIP alone
fig = plot_mip(f_vol, x_out, y_out,
               title="Wideband 3-D Reconstruction — Max-Intensity Projection")
fig.savefig(RESULTS_DIR / "wideband_mip.png", dpi=150, bbox_inches='tight')
plt.close(fig)

# 3. Range profile through peak
fig = plot_range_profile(fv, zv, title="Range Profile (Single On-Axis Target)")
fig.savefig(RESULTS_DIR / "range_profile.png", dpi=150, bbox_inches='tight')
plt.close(fig)

# 4. 3-D scatter of the multi-target volume
fig = plot_3d_scatter(f_vol, x_out, y_out, z_out,
                      threshold_db=-10.0,
                      title="3-D Wideband Reconstruction (isosurface, −10 dB threshold)")
fig.savefig(RESULTS_DIR / "3d_scatter.png", dpi=150, bbox_inches='tight')
plt.close(fig)

print("  comparison_mip.png")
print("  wideband_mip.png")
print("  range_profile.png")
print("  3d_scatter.png")
print()
print("Done.  Open results/ to view the output images.")
