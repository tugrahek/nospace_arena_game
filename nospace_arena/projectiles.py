from __future__ import annotations

from dataclasses import dataclass

import pygame

from .config import GRID_HEIGHT, SCREEN_WIDTH, SHOT_LIFETIME, TILE_SIZE


@dataclass
class Projectile:
    x: float
    y: float
    vx: float
    vy: float
    color: tuple[int, int, int]
    radius: float = 3.0
    ttl: float = SHOT_LIFETIME

    def update(self, dt: float) -> bool:
        self.ttl -= dt
        self.x += self.vx * dt
        self.y += self.vy * dt
        if self.ttl <= 0:
            return False
        if self.x < 0 or self.x > SCREEN_WIDTH:
            return False
        if self.y < 0 or self.y > GRID_HEIGHT * TILE_SIZE:
            return False
        return True

    def draw(self, surface: pygame.Surface) -> None:
        center = (int(self.x), int(self.y))
        glow = max(4, int(self.radius) + 4)
        sprite = pygame.Surface((glow * 4, glow * 4), pygame.SRCALPHA)
        mid = glow * 2
        pygame.draw.circle(sprite, (*self.color, 26), (mid, mid), glow + 4)
        pygame.draw.circle(sprite, (*self.color, 72), (mid, mid), glow)
        surface.blit(sprite, (center[0] - mid, center[1] - mid))
        pygame.draw.circle(surface, self.color, center, int(self.radius) + 2)
        pygame.draw.circle(surface, (255, 255, 255), center, int(self.radius), 1)
        trail_x = int(self.x - self.vx * 0.02)
        trail_y = int(self.y - self.vy * 0.02)
        pygame.draw.line(surface, (255, 255, 255), (trail_x, trail_y), center, 1)
        pygame.draw.line(surface, self.color, (trail_x, trail_y), center, 3)
