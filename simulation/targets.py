"""
simulation/targets.py
=====================
Defines target reflectivity scenes as collections of point scatterers.

Each PointTarget represents an idealised isotropic reflector at a known
(x, y, z) position.  The Scene class collects one or more targets and
provides helper methods used by the simulator and the ML dataset generator.

Physical coordinates throughout this project follow the convention in
Sheen et al. (2001):
  - z = 0 at the scan aperture plane
  - z > 0 pointing away from the aperture toward the targets
  - (x, y) spanning the aperture / scene cross-section
"""

from __future__ import annotations

import dataclasses
import numpy as np
from typing import Sequence


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclasses.dataclass
class PointTarget:
    """A single isotropic point scatterer.

    Parameters
    ----------
    x, y, z : float
        Position in metres.  z is the range (depth) from the aperture plane.
    amplitude : complex
        Complex reflectivity amplitude.  Defaults to 1.0 (unit reflector).
    label : str
        Human-readable tag used in plots and dataset annotations.
    """
    x: float
    y: float
    z: float
    amplitude: complex = 1.0 + 0j
    label: str = "target"

    def position(self) -> np.ndarray:
        """Return position as a (3,) array [x, y, z]."""
        return np.array([self.x, self.y, self.z], dtype=float)


@dataclasses.dataclass
class Scene:
    """A collection of point targets forming a single measurement scene.

    Attributes
    ----------
    targets : list[PointTarget]
        All scatterers in this scene.
    has_concealed_object : bool
        Ground-truth label for the ML classifier: True if any target
        is marked as a concealed object.
    """
    targets: list[PointTarget] = dataclasses.field(default_factory=list)
    has_concealed_object: bool = False

    def add(self, target: PointTarget) -> "Scene":
        self.targets.append(target)
        return self

    def __len__(self) -> int:
        return len(self.targets)

    def __iter__(self):
        return iter(self.targets)


# ---------------------------------------------------------------------------
# Scene factory functions
# ---------------------------------------------------------------------------

def make_single_target(
    x: float = 0.0,
    y: float = 0.0,
    z: float = 0.5,
    amplitude: complex = 1.0 + 0j,
) -> Scene:
    """Single point target — used for unit-test ground-truth validation.

    Parameters
    ----------
    x, y : float
        Cross-range position in metres (default: centre of aperture).
    z : float
        Range depth in metres from aperture plane (default: 0.5 m).
    amplitude : complex
        Reflectivity (default: unit).
    """
    target = PointTarget(x=x, y=y, z=z, amplitude=amplitude, label="single")
    return Scene(targets=[target], has_concealed_object=True)


def make_multi_depth_scene(
    depths: Sequence[float] = (0.3, 0.5, 0.7),
    x_offsets: Sequence[float] | None = None,
    y_offsets: Sequence[float] | None = None,
) -> Scene:
    """Multiple point targets at different depths.

    Used to verify that the wideband reconstruction focuses correctly at
    each target's true depth, while the single-frequency reconstruction
    blurs targets away from its focal depth (see paper Fig. 5–7).

    Parameters
    ----------
    depths : sequence of float
        Range depths (m) for each target.
    x_offsets : sequence of float, optional
        Cross-range x offsets (m); defaults to 0 for all.
    y_offsets : sequence of float, optional
        Cross-range y offsets (m); defaults to 0 for all.
    """
    n = len(depths)
    x_offsets = list(x_offsets) if x_offsets is not None else [0.0] * n
    y_offsets = list(y_offsets) if y_offsets is not None else [0.0] * n

    scene = Scene(has_concealed_object=True)
    for i, (z, xo, yo) in enumerate(zip(depths, x_offsets, y_offsets)):
        scene.add(PointTarget(x=xo, y=yo, z=z, label=f"target_z{z:.2f}m"))
    return scene


def make_weapon_scene(
    z: float = 0.5,
    width: float = 0.04,
    height: float = 0.12,
    nx_pts: int = 5,
    ny_pts: int = 12,
    x_center: float = 0.05,
    y_center: float = 0.0,
    amplitude: complex = 1.0 + 0j,
    rng: np.random.Generator | None = None,
) -> Scene:
    """Extended reflector approximating a concealed metallic weapon silhouette.

    The weapon is modelled as a dense 2-D grid of point scatterers at depth z,
    spanning (width × height) metres. Random amplitude jitter is applied to
    simulate surface roughness.

    Parameters
    ----------
    z : float
        Range depth of the weapon plane.
    width, height : float
        Physical size in x and y (metres).
    nx_pts, ny_pts : int
        Number of point scatterers along each dimension.
    x_center, y_center : float
        Centre of the weapon in the aperture plane.
    amplitude : complex
        Mean complex reflectivity.
    rng : numpy Generator, optional
        Random number generator for reproducible jitter.
    """
    if rng is None:
        rng = np.random.default_rng(42)

    xs = np.linspace(x_center - width / 2, x_center + width / 2, nx_pts)
    ys = np.linspace(y_center - height / 2, y_center + height / 2, ny_pts)

    scene = Scene(has_concealed_object=True)
    for xi in xs:
        for yi in ys:
            # Small random amplitude jitter (±10 %)
            jitter = 1.0 + 0.1 * (rng.random() - 0.5)
            scene.add(PointTarget(
                x=xi, y=yi, z=z,
                amplitude=amplitude * jitter,
                label="weapon",
            ))
    return scene


def make_clean_scene() -> Scene:
    """Empty scene with no targets — the 'clean / no threat' class."""
    return Scene(targets=[], has_concealed_object=False)
