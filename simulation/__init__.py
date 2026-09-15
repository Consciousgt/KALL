"""
simulation/__init__.py — mmwave-imaging simulation package.
"""
from .targets import PointTarget, Scene, make_single_target, make_multi_depth_scene, make_weapon_scene
from .array_sim import ApertureConfig, simulate_scattered_field

__all__ = [
    "PointTarget",
    "Scene",
    "make_single_target",
    "make_multi_depth_scene",
    "make_weapon_scene",
    "ApertureConfig",
    "simulate_scattered_field",
]
