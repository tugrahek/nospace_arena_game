from __future__ import annotations

from collections import deque

import pygame

from .config import FREE, GRID_HEIGHT, SCREEN_WIDTH, SOLID, TILE_SIZE, TRAIL


def blend(color_a, color_b, ratio: float):
    ratio = max(0.0, min(1.0, ratio))
    return tuple(int(color_a[index] * (1.0 - ratio) + color_b[index] * ratio) for index in range(3))


class Arena:
    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        self.grid = [[FREE for _ in range(width)] for _ in range(height)]
        self.trail_cells: list[tuple[int, int]] = []
        self.recent_capture_cells: list[tuple[int, int]] = []
        self.recent_capture_lookup: dict[tuple[int, int], float] = {}

        for x in range(width):
            self.grid[0][x] = SOLID
            self.grid[height - 1][x] = SOLID
        for y in range(height):
            self.grid[y][0] = SOLID
            self.grid[y][width - 1] = SOLID

        self.initial_free_cells = (width - 2) * (height - 2)
        self.free_cells = self.initial_free_cells
        self.trail_count = 0

    def in_bounds(self, x: int, y: int) -> bool:
        return 0 <= x < self.width and 0 <= y < self.height

    def cell(self, x: int, y: int) -> int:
        if not self.in_bounds(x, y):
            return SOLID
        return self.grid[y][x]

    def is_free(self, x: int, y: int) -> bool:
        return self.cell(x, y) == FREE

    def is_solid(self, x: int, y: int) -> bool:
        return self.cell(x, y) == SOLID

    def add_trail(self, x: int, y: int) -> None:
        if self.grid[y][x] == FREE:
            self.grid[y][x] = TRAIL
            self.trail_cells.append((x, y))
            self.trail_count += 1
            self.free_cells -= 1

    def clear_trail(self) -> None:
        if not self.trail_cells:
            return
        for x, y in self.trail_cells:
            self.grid[y][x] = FREE
        self.free_cells += self.trail_count
        self.trail_cells.clear()
        self.trail_count = 0

    def remove_last_trail_cell(self):
        if not self.trail_cells:
            return None
        x, y = self.trail_cells.pop()
        self.grid[y][x] = FREE
        self.trail_count -= 1
        self.free_cells += 1
        return x, y

    def free_ratio(self) -> float:
        return (self.free_cells + self.trail_count) / self.initial_free_cells

    def _seed_near_enemy(self, cx: int, cy: int):
        candidates = [(cx, cy)]
        for radius in range(1, 3):
            for dy in range(-radius, radius + 1):
                for dx in range(-radius, radius + 1):
                    candidates.append((cx + dx, cy + dy))
        for x, y in candidates:
            if self.in_bounds(x, y) and self.grid[y][x] == FREE:
                return x, y
        return None

    def finalize_capture(self, enemy_cells: list[tuple[int, int]]):
        if not self.trail_cells:
            return 0, []

        trail_snapshot = list(self.trail_cells)
        for x, y in trail_snapshot:
            self.grid[y][x] = SOLID

        self.trail_cells.clear()
        self.trail_count = 0

        reachable = [[False for _ in range(self.width)] for _ in range(self.height)]
        queue = deque()

        for ex, ey in enemy_cells:
            seed = self._seed_near_enemy(ex, ey)
            if seed is None:
                continue
            sx, sy = seed
            if not reachable[sy][sx]:
                reachable[sy][sx] = True
                queue.append((sx, sy))

        while queue:
            x, y = queue.popleft()
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx, ny = x + dx, y + dy
                if self.in_bounds(nx, ny) and not reachable[ny][nx] and self.grid[ny][nx] == FREE:
                    reachable[ny][nx] = True
                    queue.append((nx, ny))

        captured = []
        for y in range(1, self.height - 1):
            for x in range(1, self.width - 1):
                if self.grid[y][x] == FREE and not reachable[y][x]:
                    self.grid[y][x] = SOLID
                    captured.append((x, y))

        self.recent_capture_cells = captured
        self.recent_capture_lookup = {}
        if captured:
            pivot_x = sum(x for x, _ in trail_snapshot) / len(trail_snapshot)
            pivot_y = sum(y for _, y in trail_snapshot) / len(trail_snapshot)
            max_dist = max(abs(x - pivot_x) + abs(y - pivot_y) for x, y in captured) or 1.0
            self.recent_capture_lookup = {
                (x, y): (abs(x - pivot_x) + abs(y - pivot_y)) / max_dist for x, y in captured
            }

        self.free_cells -= len(captured)
        return len(captured), captured

    def draw(self, surface: pygame.Surface, theme, pulse: float, flash_ratio: float, capture_progress: float = 1.0, danger_ratio: float = 0.0) -> None:
        play_rect = pygame.Rect(0, 0, SCREEN_WIDTH, GRID_HEIGHT * TILE_SIZE)
        pygame.draw.rect(surface, theme.free_area, play_rect)
        grid_color = blend(theme.border, theme.free_area, 0.82)
        for x in range(0, SCREEN_WIDTH, TILE_SIZE * 4):
            alpha = 22 if (x // TILE_SIZE) % 10 else 34
            pygame.draw.line(surface, blend(grid_color, theme.accent, 0.12), (x, 0), (x, play_rect.bottom), 1 if alpha < 30 else 2)
        for y in range(0, play_rect.height, TILE_SIZE * 4):
            alpha = 20 if (y // TILE_SIZE) % 10 else 30
            pygame.draw.line(surface, blend(grid_color, theme.overlay, 0.14), (0, y), (play_rect.right, y), 1 if alpha < 26 else 2)

        previous_clip = surface.get_clip()
        surface.set_clip(play_rect)

        trail_boost = 1.0 + danger_ratio * 0.3
        trail_color = tuple(min(255, int(theme.trail[index] * (0.94 + 0.24 * pulse) * trail_boost)) for index in range(3))
        glow_color = theme.trail_glow
        capture_lookup = self.recent_capture_lookup if (flash_ratio > 0 or capture_progress < 1.0) else {}

        for y in range(self.height):
            for x in range(self.width):
                cell = self.grid[y][x]
                if cell == FREE:
                    continue
                rect = pygame.Rect(x * TILE_SIZE, y * TILE_SIZE, TILE_SIZE, TILE_SIZE)

                if cell == TRAIL:
                    halo = rect.inflate(8, 8)
                    pygame.draw.rect(surface, blend(glow_color, theme.free_area, 0.35), halo, border_radius=3)
                    pygame.draw.rect(surface, glow_color, rect.inflate(4, 4), border_radius=2)
                    pygame.draw.rect(surface, trail_color, rect, border_radius=2)
                    pygame.draw.rect(surface, (255, 255, 255), rect.inflate(-2, -2), 1, border_radius=2)
                    continue

                color = theme.solid_area
                reveal = capture_lookup.get((x, y))
                if reveal is not None and capture_progress < 1.0 and capture_progress < reveal:
                    wave = max(0.0, min(1.0, (capture_progress - max(0.0, reveal - 0.15)) / 0.15))
                    color = blend(theme.free_area, theme.solid_area, 0.18 + wave * 0.62)
                elif reveal is not None and flash_ratio > 0:
                    color = blend(color, theme.overlay, 0.38 + flash_ratio * 0.52)
                elif cell == SOLID and 0 < x < self.width - 1 and 0 < y < self.height - 1:
                    color = blend(color, theme.overlay, 0.08 + pulse * 0.05)
                pygame.draw.rect(surface, color, rect)

        surface.set_clip(previous_clip)
        pygame.draw.rect(surface, blend(theme.border, theme.overlay, 0.26), play_rect.inflate(-2, -2), 1)
        pygame.draw.rect(surface, theme.border, play_rect, 3)
        pygame.draw.rect(surface, blend(theme.border, (255, 255, 255), 0.2), play_rect.inflate(-8, -8), 1)
