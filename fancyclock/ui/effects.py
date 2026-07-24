"""Galaxy starfield effect used as the default clock background."""

from __future__ import annotations

import math
import random

from PySide6.QtGui import QColor

SPIRAL_ARMS: tuple[int, ...] = (0, 1, 2, 3)
MIN_SPAWN_RADIUS = 10.0
MIN_WRAP_RADIUS = 8.0
MIN_ANGULAR_VELOCITY = 0.002
MAX_ANGULAR_VELOCITY = 0.012
MIN_RADIAL_VELOCITY = -0.05
MAX_RADIAL_VELOCITY = 0.10
ARM_ANGLE_STEP = 0.002
MIN_STAR_SIZE = 1.0
MAX_STAR_SIZE = 2.0
STAR_BASE_COLORS: tuple[tuple[int, int, int], ...] = (
    (255, 255, 255),
    (220, 220, 255),
    (255, 240, 190),
)
SHIMMER_RANGE = 3
CHANNEL_MIN = 150
CHANNEL_MAX = 255


class GalaxyStar:
    """A spiral galaxy star that orbits, drifts and shimmers subtly."""

    def __init__(self, max_radius: float):
        self.max_radius = max_radius

        self.arm = random.choice(SPIRAL_ARMS)

        self.radius = random.uniform(MIN_SPAWN_RADIUS, max_radius)
        self.angle = random.uniform(0, math.tau)

        self.angular_velocity = random.uniform(
            MIN_ANGULAR_VELOCITY, MAX_ANGULAR_VELOCITY
        )
        self.radial_velocity = random.uniform(MIN_RADIAL_VELOCITY, MAX_RADIAL_VELOCITY)

        self.size = random.uniform(MIN_STAR_SIZE, MAX_STAR_SIZE)

        self.r, self.g, self.b = random.choice(STAR_BASE_COLORS)

    def update(self):
        """Move the star along a spiral path."""
        self.angle += self.angular_velocity
        self.angle += self.arm * ARM_ANGLE_STEP
        self.radius += self.radial_velocity

        if self.radius > self.max_radius or self.radius < MIN_WRAP_RADIUS:
            self.radius = random.uniform(MIN_SPAWN_RADIUS, self.max_radius)
            self.angle = random.uniform(0, math.tau)

        drift = random.randint(-SHIMMER_RANGE, SHIMMER_RANGE)
        self.r = min(CHANNEL_MAX, max(CHANNEL_MIN, self.r + drift))
        self.g = min(CHANNEL_MAX, max(CHANNEL_MIN, self.g + drift))
        self.b = min(CHANNEL_MAX, max(CHANNEL_MIN, self.b + drift))

    def pos(self):
        """Return absolute (x, y) within a centered coordinate system."""
        x = self.radius * math.cos(self.angle)
        y = self.radius * math.sin(self.angle)
        return x, y

    def color(self):
        return QColor(self.r, self.g, self.b)


def create_galaxy(count: int, radius: float):
    """Return ``count`` stars distributed within ``radius``."""
    return [GalaxyStar(radius) for _ in range(count)]
