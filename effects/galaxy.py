import random
import math
from PySide6.QtGui import QColor


class GalaxyStar:
    """
    A dynamic spiral galaxy star that moves along curved arms,
    drifts in/out, and shimmers subtly.
    """

    def __init__(self, max_radius: float):
        self.max_radius = max_radius

        # Spiral structure: choose one of several arms
        self.arm = random.choice([0, 1, 2, 3])

        # Initial orbital position
        self.radius = random.uniform(10, max_radius)
        self.angle = random.uniform(0, math.tau)

        # Motion parameters
        self.angular_velocity = random.uniform(0.002, 0.012)
        self.radial_velocity = random.uniform(-0.05, 0.10)

        # Appearance
        self.size = random.uniform(1.0, 2.0)

        # Color variations (cool blues, warm whites)
        base = random.choice([
            (255, 255, 255),
            (220, 220, 255),
            (255, 240, 190)
        ])
        self.r, self.g, self.b = base

    def update(self):
        """Move the star along a spiral path."""
        self.angle += self.angular_velocity
        self.angle += self.arm * 0.002
        self.radius += self.radial_velocity

        # Wrap if the star drifts too far
        if self.radius > self.max_radius or self.radius < 8:
            self.radius = random.uniform(10, self.max_radius)
            self.angle = random.uniform(0, math.tau)

        # Color shimmer
        drift = random.randint(-3, 3)
        self.r = min(255, max(150, self.r + drift))
        self.g = min(255, max(150, self.g + drift))
        self.b = min(255, max(150, self.b + drift))

    def pos(self):
        """Return absolute (x,y) within a centered coordinate system."""
        x = self.radius * math.cos(self.angle)
        y = self.radius * math.sin(self.angle)
        return x, y

    def color(self):
        return QColor(self.r, self.g, self.b)


def create_galaxy(count: int, radius: float):
    return [GalaxyStar(radius) for _ in range(count)]
