from __future__ import annotations

import math
import random

import pygame


class ParticleSystem:
    def __init__(self):
        self.particles: list[dict] = []
        self.max_particles = 900

    def _push(self, particle: dict) -> None:
        self.particles.append(particle)
        overflow = len(self.particles) - self.max_particles
        if overflow > 0:
            del self.particles[:overflow]

    def emit_burst(self, x: float, y: float, color, count: int, speed: float = 80.0, spread: float = math.tau) -> None:
        for _ in range(count):
            angle = random.uniform(-spread * 0.5, spread * 0.5) + random.uniform(0.0, math.tau)
            velocity = random.uniform(speed * 0.45, speed)
            self._push(
                {
                    "x": x,
                    "y": y,
                    "vx": math.cos(angle) * velocity,
                    "vy": math.sin(angle) * velocity,
                    "life": random.uniform(0.25, 0.65),
                    "max_life": 0.65,
                    "color": color,
                    "size": random.uniform(2.0, 4.8),
                    "gravity": 36.0,
                    "drag": 0.94,
                    "glow": 1.0,
                }
            )

    def emit_line(self, points: list[tuple[float, float]], color, density: int = 1, speed: float = 60.0) -> None:
        for px, py in points:
            for _ in range(max(1, density)):
                angle = random.uniform(0.0, math.tau)
                velocity = random.uniform(speed * 0.35, speed)
                self._push(
                    {
                        "x": px,
                        "y": py,
                        "vx": math.cos(angle) * velocity,
                        "vy": math.sin(angle) * velocity,
                        "life": random.uniform(0.16, 0.34),
                        "max_life": 0.34,
                        "color": color,
                        "size": random.uniform(1.4, 3.0),
                        "gravity": 12.0,
                        "drag": 0.97,
                        "glow": 0.8,
                    }
                )

    def emit_trail(self, x: float, y: float, color, direction: tuple[float, float], danger: float = 0.0) -> None:
        dx, dy = direction
        for _ in range(2 + int(danger > 0.45)):
            spread = 0.55 + danger * 0.35
            angle = math.atan2(dy or 0.01, dx or 1.0) + math.pi + random.uniform(-spread, spread)
            velocity = random.uniform(22.0, 42.0 + danger * 30.0)
            self._push(
                {
                    "x": x + random.uniform(-2.0, 2.0),
                    "y": y + random.uniform(-2.0, 2.0),
                    "vx": math.cos(angle) * velocity,
                    "vy": math.sin(angle) * velocity,
                    "life": random.uniform(0.12, 0.24),
                    "max_life": 0.24,
                    "color": color,
                    "size": random.uniform(1.4, 2.8 + danger * 0.8),
                    "gravity": -4.0,
                    "drag": 0.92,
                    "glow": 1.2,
                }
            )

    def update(self, dt: float) -> None:
        alive = []
        for particle in self.particles:
            particle["life"] -= dt
            if particle["life"] <= 0:
                continue
            particle["x"] += particle["vx"] * dt
            particle["y"] += particle["vy"] * dt
            particle["vy"] += particle["gravity"] * dt
            particle["vx"] *= particle.get("drag", 1.0)
            particle["vy"] *= particle.get("drag", 1.0)
            alive.append(particle)
        self.particles = alive

    def draw(self, surface: pygame.Surface) -> None:
        for particle in self.particles:
            alpha = int(255 * (particle["life"] / particle["max_life"]))
            scale = particle["life"] / particle["max_life"] + 0.25
            size = max(1, int(particle["size"] * scale))
            sprite = pygame.Surface((size * 4, size * 4), pygame.SRCALPHA)
            glow_size = int(size + 2 + particle.get("glow", 1.0) * 1.2)
            pygame.draw.circle(sprite, (*particle["color"], max(28, alpha // 4)), (size * 2, size * 2), glow_size)
            pygame.draw.circle(sprite, (*particle["color"], alpha), (size * 2, size * 2), size)
            surface.blit(sprite, (particle["x"] - size * 2, particle["y"] - size * 2))


class ScreenTransition:
    def __init__(self):
        self.alpha = 0.0
        self.direction = -1
        self.speed = 420.0

    def trigger(self) -> None:
        self.alpha = 255.0
        self.direction = -1

    def update(self, dt: float) -> None:
        if self.alpha <= 0 and self.direction < 0:
            self.alpha = 0.0
            return
        self.alpha += self.direction * self.speed * dt
        self.alpha = max(0.0, min(255.0, self.alpha))

    def draw(self, surface: pygame.Surface, color=(0, 0, 0)) -> None:
        if self.alpha <= 0:
            return
        overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        overlay.fill((*color, int(self.alpha)))
        surface.blit(overlay, (0, 0))


class ScreenShake:
    def __init__(self):
        self.trauma = 0.0
        self.time = 0.0
        self.offset = (0, 0)

    def add(self, amount: float) -> None:
        self.trauma = max(0.0, min(1.0, self.trauma + amount))

    def update(self, dt: float, enabled: bool = True) -> None:
        self.time += dt
        self.trauma = max(0.0, self.trauma - dt * 1.7)
        if not enabled or self.trauma <= 0:
            self.offset = (0, 0)
            return
        strength = self.trauma * self.trauma
        max_offset = 14.0 * strength
        self.offset = (
            int(math.sin(self.time * 41.0) * max_offset),
            int(math.cos(self.time * 37.0) * max_offset),
        )

    def apply(self, source: pygame.Surface, target: pygame.Surface) -> None:
        target.fill((0, 0, 0))
        target.blit(source, self.offset)
