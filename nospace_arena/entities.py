from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import ClassVar

import pygame

from .config import BASE_PLAYER_STEPS_PER_SECOND, FREE, GRID_HEIGHT, SCREEN_WIDTH, SOLID, TILE_SIZE, TRAIL


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def random_unit_vector() -> tuple[float, float]:
    angle = random.uniform(0.0, math.tau)
    return math.cos(angle), math.sin(angle)


def world_from_cell(cell_x: int, cell_y: int) -> tuple[float, float]:
    return cell_x * TILE_SIZE + TILE_SIZE / 2, cell_y * TILE_SIZE + TILE_SIZE / 2


def draw_soft_glow(surface: pygame.Surface, x: float, y: float, color, radius: float, alpha: int) -> None:
    radius = max(2, int(radius))
    sprite = pygame.Surface((radius * 4, radius * 4), pygame.SRCALPHA)
    center = radius * 2
    pygame.draw.circle(sprite, (*color, max(10, alpha // 3)), (center, center), radius + 5)
    pygame.draw.circle(sprite, (*color, max(24, alpha)), (center, center), radius)
    surface.blit(sprite, (x - center, y - center))


class Player:
    def __init__(self, start_x: int, start_y: int, profile):
        self.start_x = start_x
        self.start_y = start_y
        self.profile = profile
        self.move_accumulator = 0.0
        self.animation_time = 0.0
        self.bonus_speed_multiplier = 1.0
        self.bonus_draw_multiplier = 1.0
        self.speed_boost_timer = 0.0
        self.shield_timer = profile.shield_duration
        self.blaster_timer = 0.0
        self.facing = (1, 0)
        self.trail_start_cell: tuple[int, int] | None = None
        self.reset_position()

    def reset_position(self) -> None:
        self.x = self.start_x
        self.y = self.start_y
        self.visual_x = float(self.x)
        self.visual_y = float(self.y)
        self.drawing = False
        self.trail_start_cell = None

    def give_shield(self, duration: float) -> None:
        self.shield_timer = max(self.shield_timer, duration)

    def give_blaster(self, duration: float) -> None:
        self.blaster_timer = max(self.blaster_timer, duration)

    def has_shield(self) -> bool:
        return self.shield_timer > 0

    def can_shoot(self) -> bool:
        return self.blaster_timer > 0

    def consume_shield(self) -> bool:
        if self.shield_timer > 0:
            self.shield_timer = 0.0
            return True
        return False

    def handle_death(self, arena) -> None:
        arena.clear_trail()
        self.move_accumulator = 0.0
        self.reset_position()
        self.shield_timer = max(self.shield_timer, self.profile.shield_duration)

    def _step_time(self) -> float:
        step_rate = BASE_PLAYER_STEPS_PER_SECOND * self.profile.speed_multiplier * self.bonus_speed_multiplier
        if self.drawing:
            step_rate *= self.profile.drawing_multiplier * self.bonus_draw_multiplier
            if self.speed_boost_timer > 0:
                step_rate *= 1.45
        return 1.0 / step_rate

    def update(self, dt: float, arena, input_dir):
        self.animation_time += dt
        self.speed_boost_timer = max(0.0, self.speed_boost_timer - dt)
        self.shield_timer = max(0.0, self.shield_timer - dt)
        self.blaster_timer = max(0.0, self.blaster_timer - dt)
        self.move_accumulator += dt
        result = None

        while self.move_accumulator >= self._step_time():
            self.move_accumulator -= self._step_time()
            dx, dy = input_dir
            if dx == 0 and dy == 0:
                continue
            self.facing = (dx, dy)

            nx, ny = self.x + dx, self.y + dy
            if not arena.in_bounds(nx, ny):
                continue
            target = arena.cell(nx, ny)

            if not self.drawing:
                if target == SOLID:
                    self.x, self.y = nx, ny
                elif target == FREE:
                    self.drawing = True
                    self.x, self.y = nx, ny
                    self.trail_start_cell = (self.x, self.y)
                    arena.add_trail(nx, ny)
                    result = result or "drawing"
            else:
                if target == FREE:
                    self.x, self.y = nx, ny
                    arena.add_trail(nx, ny)
                elif target == SOLID:
                    self.x, self.y = nx, ny
                    self.drawing = False
                    self.trail_start_cell = None
                    result = "captured"
                    break
                elif target == TRAIL:
                    if len(arena.trail_cells) >= 2 and (nx, ny) == arena.trail_cells[-2]:
                        arena.remove_last_trail_cell()
                        self.x, self.y = nx, ny
                    else:
                        result = "dead"
                        break
        blend = min(1.0, dt * 18.0)
        self.visual_x += (self.x - self.visual_x) * blend
        self.visual_y += (self.y - self.visual_y) * blend
        return result

    def draw(self, surface: pygame.Surface, pulse: float, danger_ratio: float = 0.0) -> None:
        cx = int(self.visual_x * TILE_SIZE + TILE_SIZE // 2)
        cy = int(self.visual_y * TILE_SIZE + TILE_SIZE // 2)
        radius = max(4, TILE_SIZE // 2)
        primary = self.profile.primary
        secondary = self.profile.secondary
        trail_core = tuple(min(255, int(channel * (1.08 + danger_ratio * 0.32))) for channel in self.profile.trail)
        aura_alpha = int(36 + pulse * 20 + danger_ratio * 48)

        draw_soft_glow(surface, cx, cy, self.profile.trail, radius + 10 + pulse * 2, aura_alpha)
        if self.drawing:
            draw_soft_glow(surface, cx, cy, trail_core, radius + 15 + danger_ratio * 5, int(42 + danger_ratio * 60))

        if self.profile.style == "diamond":
            points = [(cx, cy - radius - 2), (cx + radius + 2, cy), (cx, cy + radius + 2), (cx - radius - 2, cy)]
            pygame.draw.polygon(surface, secondary, points)
            inner = [(cx, cy - radius), (cx + radius, cy), (cx, cy + radius), (cx - radius, cy)]
            pygame.draw.polygon(surface, primary, inner)
        elif self.profile.style == "shield":
            rect = pygame.Rect(cx - radius, cy - radius, radius * 2, radius * 2 + 2)
            pygame.draw.ellipse(surface, secondary, rect)
            pygame.draw.ellipse(surface, primary, rect.inflate(-4, -4))
        elif self.profile.style == "star":
            points = []
            for index in range(10):
                angle = math.tau * index / 10.0 - math.pi / 2
                dist = radius + 3 if index % 2 == 0 else radius * 0.48
                points.append((cx + math.cos(angle) * dist, cy + math.sin(angle) * dist))
            pygame.draw.polygon(surface, secondary, points)
            pygame.draw.circle(surface, primary, (cx, cy), radius - 1)
        elif self.profile.style == "chevron":
            chevron = [(cx - radius - 1, cy - radius + 1), (cx, cy - 1), (cx + radius + 2, cy - radius + 1), (cx + 3, cy + radius + 1), (cx, cy + 2), (cx - 3, cy + radius + 1)]
            pygame.draw.polygon(surface, secondary, chevron)
            inner = [(cx - radius + 1, cy - radius + 1), (cx, cy), (cx + radius, cy - radius + 1), (cx + 2, cy + radius - 1), (cx, cy + 1), (cx - 2, cy + radius - 1)]
            pygame.draw.polygon(surface, primary, inner)
        else:
            pygame.draw.circle(surface, secondary, (cx, cy), radius + 2)
            pygame.draw.circle(surface, primary, (cx, cy), radius)

        nose_x = cx + self.facing[0] * (radius + 4)
        nose_y = cy + self.facing[1] * (radius + 4)
        pygame.draw.line(surface, (255, 255, 255), (cx, cy), (nose_x, nose_y), 2)
        pygame.draw.circle(surface, (255, 255, 255), (nose_x, nose_y), 2)
        pygame.draw.circle(surface, (10, 16, 26), (cx, cy), max(1, radius - 3), 1)

        if self.drawing:
            glow_radius = int(radius + 7 + pulse * 2 + danger_ratio * 7)
            pygame.draw.circle(surface, trail_core, (cx, cy), glow_radius, 2)
            pygame.draw.circle(surface, (255, 255, 255), (cx, cy), max(3, radius - 1), 1)
        if self.can_shoot():
            draw_soft_glow(surface, cx, cy, (255, 120, 120), radius + 13 + pulse * 2, 38)
            pygame.draw.circle(surface, (255, 170, 170), (cx, cy), int(radius + 9 + pulse * 2), 1)
        if self.has_shield():
            draw_soft_glow(surface, cx, cy, (255, 226, 132), radius + 14 + pulse * 2, 36)
            shield_radius = int(radius + 7 + pulse * 1.5)
            pygame.draw.circle(surface, (255, 244, 140), (cx, cy), shield_radius, 1)
        if danger_ratio > 0:
            draw_soft_glow(surface, cx, cy, (255, 96, 96), radius + 18 + pulse * 2 + danger_ratio * 5, int(24 + danger_ratio * 48))
            warning_radius = int(radius + 10 + pulse * 3 + danger_ratio * 8)
            pygame.draw.circle(surface, (255, 110, 110), (cx, cy), warning_radius, 2)


class Enemy:
    COLOR_MAP = {
        "bouncer": (255, 120, 115),
        "hunter": (255, 92, 105),
        "ghost": (150, 215, 255),
        "splitter": (255, 155, 74),
        "tank": (220, 82, 255),
    }

    BEHAVIOR_STATS = {
        "bouncer": {"wobble": 0.32, "turn": 2.7, "reaction": 1.18, "aggression": 0.13, "speed": 0.96, "size": 0.95},
        "hunter": {"wobble": 0.58, "turn": 3.65, "reaction": 0.9, "aggression": 0.28, "speed": 1.03, "size": 1.0},
        "ghost": {"wobble": 0.76, "turn": 3.35, "reaction": 0.84, "aggression": 0.24, "speed": 0.98, "size": 0.92},
        "splitter": {"wobble": 1.05, "turn": 4.3, "reaction": 0.72, "aggression": 0.38, "speed": 1.08, "size": 0.88},
        "tank": {"wobble": 0.2, "turn": 2.1, "reaction": 1.06, "aggression": 0.34, "speed": 0.72, "size": 1.42},
    }

    def __init__(self, x: float, y: float, speed: float, behavior: str = "bouncer", level: int = 1, leader: bool = False):
        self.x = x
        self.y = y
        self.base_speed = speed
        self.behavior = behavior if behavior in self.BEHAVIOR_STATS else "bouncer"
        self.level = level
        self.leader = leader
        profile = self.BEHAVIOR_STATS[self.behavior]
        size_growth = min(0.82, (level - 1) * 0.045)
        leader_bonus = 0.08 if leader else 0.0
        self.radius = TILE_SIZE * (0.54 + size_growth + leader_bonus) * profile["size"]
        self.animation_time = random.uniform(0.0, 1.0)
        self.time_alive = 0.0
        self.behavior_timer = random.uniform(0.28, 0.7)
        self.decision_timer = random.uniform(0.18, 0.55)
        self.frozen_timer = 0.0
        self.stun_timer = 0.0
        self.phase_timer = 0.0
        self.phase_cooldown = random.uniform(1.8, 3.4)
        self.intent = "patrol"
        self.target_x = x
        self.target_y = y
        self.ai_noise = random.uniform(18.0, 82.0)
        self.vx, self.vy = random_unit_vector()

    def current_speed(self, slow_factor: float, theme_speed_scale: float = 1.0) -> float:
        ramp = 1.0 + min(0.82, (self.level - 1) * 0.055 + self.time_alive * 0.018)
        behavior_bonus = self.BEHAVIOR_STATS[self.behavior]["speed"]
        leader_bonus = 1.06 if self.leader else 1.0
        return self.base_speed * ramp * behavior_bonus * leader_bonus * slow_factor * theme_speed_scale

    def _solid_collision(self, arena, x: float, y: float) -> bool:
        if self.behavior == "ghost" and self.phase_timer > 0:
            return False
        sample_points = [
            (x, y),
            (x + self.radius, y),
            (x - self.radius, y),
            (x, y + self.radius),
            (x, y - self.radius),
            (x + self.radius * 0.72, y + self.radius * 0.72),
            (x - self.radius * 0.72, y + self.radius * 0.72),
            (x + self.radius * 0.72, y - self.radius * 0.72),
            (x - self.radius * 0.72, y - self.radius * 0.72),
        ]
        for px, py in sample_points:
            cx = int(px // TILE_SIZE)
            cy = int(py // TILE_SIZE)
            if arena.cell(cx, cy) == SOLID:
                return True
        return False

    def touches_trail(self, arena) -> bool:
        for angle in range(0, 360, 45):
            radians = math.radians(angle)
            px = self.x + math.cos(radians) * self.radius
            py = self.y + math.sin(radians) * self.radius
            cx = int(px // TILE_SIZE)
            cy = int(py // TILE_SIZE)
            if arena.cell(cx, cy) == TRAIL:
                return True
        return arena.cell(int(self.x // TILE_SIZE), int(self.y // TILE_SIZE)) == TRAIL

    def cell_position(self) -> tuple[int, int]:
        return int(self.x // TILE_SIZE), int(self.y // TILE_SIZE)

    def reset_position(self, x: float, y: float) -> None:
        self.x = x
        self.y = y
        self.time_alive = 0.0
        self.frozen_timer = 0.0
        self.stun_timer = 0.0
        self.phase_timer = 0.0
        self.phase_cooldown = random.uniform(1.8, 3.4)
        self.behavior_timer = random.uniform(0.28, 0.7)
        self.decision_timer = random.uniform(0.18, 0.55)
        self.intent = "patrol"
        self.target_x = x
        self.target_y = y
        self.vx, self.vy = random_unit_vector()

    def stun(self, duration: float) -> None:
        self.stun_timer = max(self.stun_timer, duration)

    def _normalize(self) -> None:
        length = math.hypot(self.vx, self.vy)
        if length <= 0.001:
            self.vx, self.vy = random_unit_vector()
            return
        self.vx /= length
        self.vy /= length

    def _rotate(self, angle: float) -> None:
        cos_a = math.cos(angle)
        sin_a = math.sin(angle)
        self.vx, self.vy = self.vx * cos_a - self.vy * sin_a, self.vx * sin_a + self.vy * cos_a
        self._normalize()

    def _steer_toward(self, target_x: float, target_y: float, weight: float) -> None:
        dx = target_x - self.x
        dy = target_y - self.y
        distance = math.hypot(dx, dy)
        if distance < 1.0:
            return
        desired_x = dx / distance
        desired_y = dy / distance
        weight = clamp(weight, 0.0, 0.92)
        self.vx = (1.0 - weight) * self.vx + weight * desired_x
        self.vy = (1.0 - weight) * self.vy + weight * desired_y
        self._normalize()

    def _pick_idle_target(self, arena, context) -> tuple[float, float]:
        roam_margin = 8
        if context.get("player_idle", False):
            px, py = context["player_pos"]
            jitter = 150 + self.ai_noise * 0.6
            tx = clamp(px + random.uniform(-jitter, jitter), roam_margin * TILE_SIZE, SCREEN_WIDTH - roam_margin * TILE_SIZE)
            ty = clamp(py + random.uniform(-jitter, jitter), roam_margin * TILE_SIZE, GRID_HEIGHT * TILE_SIZE - roam_margin * TILE_SIZE)
            return tx, ty
        return (
            random.uniform(roam_margin * TILE_SIZE, SCREEN_WIDTH - roam_margin * TILE_SIZE),
            random.uniform(roam_margin * TILE_SIZE, GRID_HEIGHT * TILE_SIZE - roam_margin * TILE_SIZE),
        )

    def _pick_hunt_target(self, context) -> tuple[float, float]:
        samples = context.get("trail_samples", [])
        trail_head = context.get("trail_head", context["player_pos"])
        trail_entry = context.get("trail_entry", trail_head)
        predicted_head = context.get("predicted_head", trail_head)
        nearest = trail_head
        if samples:
            nearest = min(samples, key=lambda point: math.hypot(point[0] - self.x, point[1] - self.y))

        profile = self.BEHAVIOR_STATS.get(self.behavior, self.BEHAVIOR_STATS["bouncer"])
        aggression = profile["aggression"] + min(0.3, context.get("threat_strength", 0.0) * 0.5)
        if self.behavior == "tank":
            aggression *= 0.82
        elif self.behavior == "splitter":
            aggression *= 1.1
        mix_roll = random.random()
        if mix_roll < 0.25 + aggression * 0.2:
            base_x = nearest[0] * 0.55 + trail_entry[0] * 0.45
            base_y = nearest[1] * 0.55 + trail_entry[1] * 0.45
            self.intent = "cutoff"
        elif mix_roll < 0.65:
            base_x = nearest[0] * 0.45 + predicted_head[0] * 0.55
            base_y = nearest[1] * 0.45 + predicted_head[1] * 0.55
            self.intent = "intercept"
        else:
            base_x = trail_head[0] * 0.7 + predicted_head[0] * 0.3
            base_y = trail_head[1] * 0.7 + predicted_head[1] * 0.3
            self.intent = "pressure"

        noise = max(10.0, 58.0 - context.get("level", 1) * 2.2 - (12.0 if self.leader else 0.0))
        if self.behavior == "bouncer":
            noise += 20.0
        elif self.behavior == "tank":
            noise += 10.0
        elif self.behavior == "splitter":
            noise *= 0.82
        jitter_x = random.uniform(-noise, noise)
        jitter_y = random.uniform(-noise, noise)
        return base_x + jitter_x, base_y + jitter_y

    def update(self, dt: float, arena, slow_factor: float = 1.0, context=None, theme_speed_scale: float = 1.0) -> None:
        self.animation_time += dt
        self.time_alive += dt
        self.frozen_timer = max(0.0, self.frozen_timer - dt)
        self.stun_timer = max(0.0, self.stun_timer - dt)
        self.phase_timer = max(0.0, self.phase_timer - dt)
        self.phase_cooldown = max(0.0, self.phase_cooldown - dt)
        if self.behavior == "ghost" and self.phase_timer <= 0 and arena.cell(int(self.x // TILE_SIZE), int(self.y // TILE_SIZE)) == SOLID:
            self.phase_timer = 0.35
        if self.frozen_timer > 0 or self.stun_timer > 0:
            return

        context = context or {}
        profile = self.BEHAVIOR_STATS.get(self.behavior, self.BEHAVIOR_STATS["bouncer"])
        if (
            self.behavior == "ghost"
            and self.phase_timer <= 0
            and self.phase_cooldown <= 0
            and context.get("mode") == "drawing"
            and context.get("level", 1) >= 5
            and context.get("threat_strength", 0.0) > 0.34
        ):
            chance = dt * (0.42 + min(0.5, context.get("level", 1) * 0.035))
            if random.random() < chance:
                self.phase_timer = 0.75 + min(0.55, context.get("level", 1) * 0.035)
                self.phase_cooldown = random.uniform(3.2, 5.2)

        self.decision_timer -= dt
        self.behavior_timer -= dt

        if self.decision_timer <= 0.0:
            if context.get("mode") == "drawing":
                self.target_x, self.target_y = self._pick_hunt_target(context)
                reaction = context.get("drawing_reaction", 0.45) * profile["reaction"]
            else:
                self.target_x, self.target_y = self._pick_idle_target(arena, context)
                self.intent = "patrol" if context.get("player_idle", False) else "shadow"
                reaction = context.get("idle_reaction", 0.9) * (profile["reaction"] + 0.18)
            self.decision_timer = max(0.08, reaction * random.uniform(0.85, 1.15))

        if self.behavior_timer <= 0.0:
            wobble = profile["wobble"]
            if context.get("mode") == "drawing":
                wobble *= 0.7
            else:
                wobble *= 1.15
            self._rotate(random.uniform(-wobble, wobble))
            self.behavior_timer = random.uniform(0.18, 0.5 if context.get("mode") == "drawing" else 0.82)

        turn_rate = profile["turn"] + min(1.8, context.get("level", 1) * 0.09) + (0.35 if self.leader else 0.0)
        if context.get("mode") == "drawing":
            turn_rate += context.get("threat_strength", 0.0) * 1.8
        if self.behavior == "tank":
            turn_rate *= 0.82
        self._steer_toward(self.target_x, self.target_y, dt * turn_rate)

        speed = self.current_speed(slow_factor, theme_speed_scale)
        if context.get("mode") == "drawing":
            speed *= 1.0 + min(0.38, context.get("pressure", 0.0))
        elif context.get("player_idle", False):
            speed *= 0.94

        next_x = self.x + self.vx * speed * dt
        if self._solid_collision(arena, next_x, self.y):
            self.vx *= -1
            self.target_x = self.x + self.vx * 80
            if self.behavior in {"hunter", "splitter"}:
                self._rotate(random.uniform(-0.6, 0.6))
            next_x = self.x
        self.x = next_x

        next_y = self.y + self.vy * speed * dt
        if self._solid_collision(arena, self.x, next_y):
            self.vy *= -1
            self.target_y = self.y + self.vy * 80
            if self.behavior in {"hunter", "splitter"}:
                self._rotate(random.uniform(-0.6, 0.6))
            next_y = self.y
        self.y = next_y

        self.x = clamp(self.x, TILE_SIZE + self.radius, SCREEN_WIDTH - TILE_SIZE - self.radius)
        self.y = clamp(self.y, TILE_SIZE + self.radius, GRID_HEIGHT * TILE_SIZE - TILE_SIZE - self.radius)

    def draw(self, surface: pygame.Surface) -> None:
        color = self.COLOR_MAP.get(self.behavior, (255, 110, 110))
        center = (int(self.x), int(self.y))
        wobble = math.sin(self.animation_time * 7.0) * 1.8
        outer = max(4, int(self.radius + 3 + max(0.0, wobble)))
        inner = max(3, int(self.radius))
        ring_color = color
        if self.stun_timer > 0:
            color = (140, 210, 255)
            ring_color = (220, 245, 255)
        elif self.frozen_timer > 0:
            color = (190, 245, 255)
            ring_color = (255, 255, 255)
        elif self.phase_timer > 0:
            color = (190, 235, 255)
            ring_color = (255, 255, 255)

        pulse_alpha = 20 + int((math.sin(self.animation_time * 4.6) + 1.0) * 18)
        draw_soft_glow(surface, center[0], center[1], ring_color, outer + 12, pulse_alpha)
        if self.intent in {"intercept", "cutoff", "pressure"}:
            draw_soft_glow(surface, center[0], center[1], color, outer + 15, 26)

        if self.behavior == "tank":
            pygame.draw.circle(surface, ring_color, center, outer + 3)
            pygame.draw.circle(surface, (18, 18, 24), center, outer)
            pygame.draw.circle(surface, color, center, inner)
            pygame.draw.rect(surface, (18, 18, 24), pygame.Rect(center[0] - inner // 2, center[1] - 2, inner, 4), border_radius=2)
        elif self.behavior == "splitter":
            pygame.draw.circle(surface, ring_color, center, outer + 2)
            pygame.draw.circle(surface, (18, 18, 24), center, outer)
            pygame.draw.circle(surface, color, center, inner)
            pygame.draw.line(surface, (18, 18, 24), (center[0] - inner, center[1]), (center[0] + inner, center[1]), 2)
            pygame.draw.line(surface, (18, 18, 24), (center[0], center[1] - inner), (center[0], center[1] + inner), 2)
        elif self.behavior == "ghost":
            pygame.draw.circle(surface, ring_color, center, outer + 2, 2)
            pygame.draw.circle(surface, color, center, inner, 2)
            pygame.draw.circle(surface, (18, 18, 24), center, max(2, inner - 4))
        else:
            pygame.draw.circle(surface, ring_color, center, outer + 2)
            pygame.draw.circle(surface, (18, 18, 24), center, outer)
            pygame.draw.circle(surface, color, center, inner)
            pygame.draw.circle(surface, (18, 18, 24), center, max(2, inner - 3))

        eye_offset = max(2, inner // 3)
        pygame.draw.circle(surface, (255, 245, 245), (center[0] - eye_offset, center[1] - 1), 2)
        pygame.draw.circle(surface, (255, 245, 245), (center[0] + eye_offset, center[1] - 1), 2)
        if self.intent in {"intercept", "cutoff", "pressure"} and self.stun_timer <= 0 and self.frozen_timer <= 0:
            pygame.draw.circle(surface, color, center, outer + 6, 1)


@dataclass
class PowerUp:
    key: str
    x: int
    y: int
    color: tuple[int, int, int]
    label: str
    icon: str
    duration: float
    ttl: float = 14.0
    bob_time: float = 0.0

    _font: ClassVar[pygame.font.Font | None] = None

    def update(self, dt: float) -> bool:
        self.ttl -= dt
        self.bob_time += dt
        return self.ttl > 0

    def cell(self) -> tuple[int, int]:
        return self.x, self.y

    @classmethod
    def font(cls) -> pygame.font.Font:
        if cls._font is None:
            cls._font = pygame.font.SysFont("consolas", 12, bold=True)
        return cls._font

    def draw(self, surface: pygame.Surface) -> None:
        cx = self.x * TILE_SIZE + TILE_SIZE // 2
        cy = self.y * TILE_SIZE + TILE_SIZE // 2 + int(math.sin(self.bob_time * 5.0) * 2)
        radius = max(4, TILE_SIZE // 2)
        glow_radius = int(radius + 4 + (math.sin(self.bob_time * 7.0) + 1.0) * 1.4)
        draw_soft_glow(surface, cx, cy, self.color, glow_radius + 6, 28)
        pygame.draw.circle(surface, self.color, (cx, cy), glow_radius, 1)
        pygame.draw.circle(surface, self.color, (cx, cy), radius + 1)
        pygame.draw.circle(surface, (18, 18, 18), (cx, cy), max(2, radius - 1))
        glyph = self.font().render(self.icon, True, self.color)
        surface.blit(glyph, glyph.get_rect(center=(cx, cy)))
