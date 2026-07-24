"""Generate the bundled alarm sounds into assets/sounds/.

Deterministic stdlib synthesis (wave + math, no dependencies): rerunning
always produces identical files. Each sound is a short phrase designed to
loop cleanly while an alarm rings.

Run:  python generate_sounds.py
"""

from __future__ import annotations

import math
import struct
import wave
from pathlib import Path

SAMPLE_RATE = 44100
SAMPLE_WIDTH_BYTES = 2
CHANNELS = 1
PEAK = 0.8
INT16_MAX = 32767

OUTPUT_DIR = Path(__file__).resolve().parent / "assets" / "sounds"

TWO_PI = 2.0 * math.pi


def silence(seconds: float) -> list[float]:
    return [0.0] * int(SAMPLE_RATE * seconds)


def tone(
    freq_hz: float,
    seconds: float,
    attack_s: float = 0.005,
    decay_s: float = 0.05,
    partials: tuple[tuple[float, float], ...] = ((1.0, 1.0),),
    decay_rate: float = 0.0,
) -> list[float]:
    """One enveloped note built from (multiple, amplitude) partials."""
    count = int(SAMPLE_RATE * seconds)
    samples: list[float] = []
    for i in range(count):
        t = i / SAMPLE_RATE
        value = sum(
            amp * math.sin(TWO_PI * freq_hz * mult * t) for mult, amp in partials
        )
        if decay_rate:
            value *= math.exp(-decay_rate * t)
        if t < attack_s:
            value *= t / attack_s
        remaining = seconds - t
        if remaining < decay_s:
            value *= remaining / decay_s
        samples.append(value)
    return samples


def beep() -> list[float]:
    """Classic alarm: four insistent beeps then a breath."""
    note = tone(880.0, 0.14, partials=((1.0, 0.7), (2.0, 0.2), (3.0, 0.1)))
    gap = silence(0.10)
    phrase: list[float] = []
    for _ in range(4):
        phrase += note + gap
    return phrase + silence(0.5)


def chime() -> list[float]:
    """Gentle two-note chime with a soft tail."""
    first = tone(
        523.25,
        1.0,
        partials=((1.0, 0.8), (2.0, 0.25), (4.0, 0.08)),
        decay_rate=3.0,
    )
    second = tone(
        659.25,
        1.4,
        partials=((1.0, 0.8), (2.0, 0.25), (4.0, 0.08)),
        decay_rate=2.5,
    )
    return first + second + silence(0.4)


def bell() -> list[float]:
    """A rounder bell strike with inharmonic partials."""
    strike = tone(
        440.0,
        2.2,
        partials=((1.0, 0.7), (2.76, 0.25), (5.40, 0.12), (8.93, 0.05)),
        decay_rate=1.8,
    )
    return strike + silence(0.5)


def pulse() -> list[float]:
    """Digital pulse train: eight quick pips."""
    pip = tone(660.0, 0.05, partials=((1.0, 0.6), (3.0, 0.25)))
    gap = silence(0.05)
    phrase: list[float] = []
    for _ in range(8):
        phrase += pip + gap
    return phrase + silence(0.45)


def marimba() -> list[float]:
    """Soft mallet arpeggio: C, E, G."""
    phrase: list[float] = []
    for freq in (523.25, 659.25, 783.99):
        phrase += tone(
            freq,
            0.5,
            partials=((1.0, 0.8), (4.0, 0.15), (9.2, 0.05)),
            decay_rate=5.0,
        )
    return phrase + silence(0.4)


SOUNDS = {
    "beep": beep,
    "chime": chime,
    "bell": bell,
    "pulse": pulse,
    "marimba": marimba,
}


def write_wav(path: Path, samples: list[float]) -> None:
    peak = max(abs(value) for value in samples) or 1.0
    scale = PEAK / peak
    frames = b"".join(
        struct.pack("<h", int(max(-1.0, min(1.0, value * scale)) * INT16_MAX))
        for value in samples
    )
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(CHANNELS)
        handle.setsampwidth(SAMPLE_WIDTH_BYTES)
        handle.setframerate(SAMPLE_RATE)
        handle.writeframes(frames)


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for name, build in SOUNDS.items():
        target = OUTPUT_DIR / f"{name}.wav"
        write_wav(target, build())
        print(f"wrote {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
