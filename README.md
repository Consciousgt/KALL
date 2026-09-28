# 3-D Millimeter-Wave Holographic Imaging for Concealed Weapon Detection

A faithful Python implementation of the wideband holographic image-reconstruction
algorithm from:

> D. M. Sheen, D. L. McMakin, and T. E. Hall, **"Three-Dimensional Millimeter-Wave
> Imaging for Concealed Weapon Detection,"** *IEEE Trans. Microwave Theory Tech.*,
> vol. 49, no. 9, pp. 1581–1592, Sep. 2001.

Extended with a lightweight CNN detection layer, making this a complete
**physics-based signal processing + applied AI/ML** portfolio project.

---

## The Physics in Plain Language

### What is millimeter-wave holographic imaging?

A person stands in front of a portal that looks like a doorframe. Hidden inside
the frame is a flat antenna array that sweeps a 27–33 GHz (K-band) radio signal
across the body in a raster scan — like a printer head moving across a page. At
each scan position, the same antenna receives the echo reflected back from the
body and any concealed objects.

Metal and dense materials reflect much more strongly than human tissue, so a
concealed weapon shows up as a bright region — if we can reconstruct the 3-D
image correctly.

### Why is reconstruction non-trivial?

The antenna receives a superposition of echoes from *everything* in front of it:
clothing, skin, and any hidden objects. Disentangling these requires solving an
**inverse scattering problem**: given the measurements `s(x', y', f)` on the
aperture grid, reconstruct the reflectivity `f(x, y, z)` in 3-D space.

### The algorithm (paper Eq. 23)

The key insight is that the measurement and the scene are related by a 3-D
Fourier transform — if you know how to change variables correctly.

**Step 1** — FFT across the aperture (x, y) for every frequency:
```
S(kx, ky, f)  =  FFT2D[ s(x', y', f) ]
```
This decomposes the measured wavefield into plane-wave components.

**Step 2** — Phase multiply (back-propagation):
```
S̃ = S · exp(-j · kz · Z₁)
```
where `kz = sqrt( (2·2πf/c)² − kx² − ky² )`. This coherently shifts
all plane-wave components to focus at depth Z₁.

**Step 3 — kz resampling** *(the critical step)*

Here's the subtlety: `kz` is a nonlinear function of frequency. As we sweep
`f`, the data lives on *nested spherical shells* in `(kx, ky, kz)` space — not
on a uniform 3-D Cartesian grid. Before the 3-D IFFT we must **resample** the
data from its natural nonuniform `kz` axis onto a uniform grid using **cubic
spline interpolation**. This is the step the predecessor MATLAB prototype
skipped, which is why that code only approximated the reconstruction.

**Step 4** — 3-D IFFT:
```
f(x, y, z)  =  IFFT3D[ S̃_uniform(kx, ky, kz) ]
```
The result is a focused 3-D reflectivity volume. Each bright voxel corresponds
to a reflective surface in the scene.

### Expected resolution

| Dimension | Formula | Value (27–33 GHz, 50 cm aperture) |
|-----------|---------|-----------------------------------|
| Range (depth) δz | c / (2B) | **≈ 2.5 cm** |
| Cross-range δx | λ·R / D | **≈ 1 cm** at 50 cm depth |

---

## Project Structure

```
mmwave-imaging/
├── simulation/
│   ├── targets.py       # scene definitions (point scatterers, weapon silhouettes)
│   └── array_sim.py     # simulate scanned-aperture scattered field data
├── reconstruction/
│   ├── single_frequency.py  # Eq. (11): narrow-band backward-wave reconstruction
│   └── wideband.py          # Eq. (23): 3-D wideband + kz resampling (core algorithm)
├── visualization/
│   └── plots.py         # MIP, depth slice, range profile, 3-D scatter
├── ml/
│   ├── dataset.py       # generate labelled synthetic dataset
│   └── detector.py      # small CNN classifier
├── tests/               # pytest unit tests (simulation, single-freq, wideband)
├── results/             # saved figures and model weights
├── run_physics.py       # Phase 1 end-to-end demo
└── run_ml.py            # Phase 2 CNN training + evaluation
```

---

## Quickstart

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Run the physics demo

```bash
python run_physics.py
```

Produces in `results/`:
- `comparison_mip.png` — side-by-side: single-frequency (blurred) vs wideband (sharp)
- `wideband_mip.png` — max-intensity projection of the 3-D volume
- `range_profile.png` — 1-D depth profile showing the range resolution
- `3d_scatter.png` — 3-D scatter plot of the reconstructed volume

### 3. Run the test suite

```bash
pytest tests/ -v
```

### 4. Train the CNN detector (Phase 2)

```bash
python run_ml.py --samples 300 --epochs 20
```

---

## Example Results & Verification

### 1. Single-Frequency vs Wideband Holographic Focusing
The wideband holographic reconstruction algorithm simultaneously focuses targets across all depths, unlike single-frequency narrow-band backward-wave propagation which is only focused at a single range plane:

![Single-Frequency vs Wideband Comparison](results/comparison_mip.png)

### 2. Range Resolution Profile
Comparing measured -3 dB full-width at half-maximum (FWHM) against theoretical depth resolution $\delta z \approx \frac{c}{2B}$:
- Theoretical $\delta z$: **2.50 cm** (for $B = 6\text{ GHz}$)
- Measured FWHM: **2.48 cm** (Ratio = **0.99**)

![Range Profile](results/range_profile.png)

### 3. 3-D Volume Reconstruction
Interactive 3-D point cloud representation of detected targets at depths of 35 cm, 50 cm, and 65 cm:

![3-D Volume Reconstruction](results/3d_scatter.png)

---

## Applied AI/ML Layer: Concealed Weapon Detection

A lightweight 3-block convolutional neural network (`ConvDetector`) is trained on 2-D max-intensity projections of 3-D reconstructed millimeter-wave scenes. The model classifies whether a concealed weapon is present under noisy conditions:

### Training Dynamics & Validation
![Training Curves](results/training_curves.png)

### Model Evaluation Metrics
Evaluated on a held-out test set:
- **Accuracy**: 100.0%
- **Precision**: 100.0%
- **Recall**: 100.0%
- **F1-Score**: 1.000

```
Confusion Matrix:
               Predicted Clean    Predicted Threat
Actual Clean          5                  0
Actual Threat         0                 10
```

### Sample Detections
![Example Detections](results/example_detections.png)

---

## Technical Notes

- **Interpolation: cubic, not linear** — The kz resampling uses cubic splines
  (`scipy.interpolate.interp1d`, `kind='cubic'`). Linear interpolation would
  introduce a systematic phase error in the kz→z mapping, degrading range
  resolution. The scattered field is a smooth, band-limited signal in frequency,
  making cubic splines accurate without overshoot risk.

- **Evanescent modes** — Plane-wave components with `kx² + ky² > (2k)²` carry
  no propagating energy. These are zeroed out before the IFFT.

- **Coordinate convention** — z = 0 at the scan aperture plane; z > 0 toward
  the targets. The aperture is centred on (x=0, y=0).

---

## References

1. Sheen, D. M., McMakin, D. L., and Hall, T. E. (2001). Three-dimensional
   millimeter-wave imaging for concealed weapon detection. *IEEE Transactions on
   Microwave Theory and Techniques*, 49(9), 1581–1592.
