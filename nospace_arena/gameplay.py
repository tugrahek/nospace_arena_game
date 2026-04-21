from __future__ import annotations

import math
import random

import pygame

from .arena import Arena
from .config import (
    CAPTURE_ANIMATION_DURATION,
    CAPTURE_AREA_BONUS,
    CAPTURE_BASE_SCORE,
    CAPTURE_TRAIL_BONUS,
    BOMB_RADIUS,
    BOMB_STUN_DURATION,
    COMBO_WINDOW,
    DANGER_RADIUS,
    DRAWING_ENEMY_REACTION,
    GRID_HEIGHT,
    GRID_WIDTH,
    IDLE_ENEMY_REACTION,
    MAX_POWERUPS,
    POWERUP_SAFE_RADIUS,
    POWERUP_SPAWN_INTERVAL,
    SHOT_COOLDOWN,
    SHOT_SPEED,
    SHOT_STUN_DURATION,
    STARTING_LIVES,
    TARGET_FREE_RATIO,
    TILE_SIZE,
)
from .content import BOOSTS, CHARACTERS, DIFFICULTIES, POWER_UPS, THEMES
from .entities import Enemy, Player, PowerUp
from .projectiles import Projectile


class GameSession:
    def __init__(
        self,
        audio,
        particles,
        shake,
        character_key: str,
        theme_key: str,
        difficulty_key: str = "arcade",
        assist_mode: bool = True,
        equipped_boost: str = "",
        starting_level: int = 1,
    ):
        self.audio = audio
        self.particles = particles
        self.shake = shake
        self.character_key = character_key
        self.theme_key = theme_key
        self.difficulty_key = difficulty_key
        self.assist_mode = assist_mode
        self.equipped_boost_key = equipped_boost if equipped_boost in BOOSTS else ""
        self.starting_level = max(1, starting_level)
        self.level = self.starting_level
        self.score = 0
        self.state = "playing"
        self.capture_flash_timer = 0.0
        self.capture_animation_timer = 0.0
        self.slow_timer = 0.0
        self.freeze_timer = 0.0
        self.powerups: list[PowerUp] = []
        self.projectiles: list[Projectile] = []
        self.powerup_spawn_timer = POWERUP_SPAWN_INTERVAL * 0.65
        self.last_move_sound = 0.0
        self.shot_cooldown = 0.0
        self.toast = ""
        self.toast_timer = 0.0
        self.combo_chain = 0
        self.combo_timer = 0.0
        self.best_combo = 1.0
        self.last_capture_points = 0
        self.last_capture_area = 0
        self.last_capture_risk = 0
        self.last_capture_percent = 0.0
        self.draw_exposure_time = 0.0
        self.idle_timer = 0.0
        self.danger_level = 0.0
        self.pending_coin_reward = 0
        self.level_reward_granted = False
        self.daily_counters = {
            "score": 0,
            "captures": 0,
            "powerups": 0,
            "stuns": 0,
            "levels": 0,
            "big_capture": 0.0,
        }
        self.difficulty = DIFFICULTIES[self.difficulty_key]
        self.boost = BOOSTS.get(self.equipped_boost_key)
        self.lives = STARTING_LIVES + self.profile.extra_lives + self.difficulty.extra_lives
        self.start_level(self.starting_level)

    @property
    def profile(self):
        return CHARACTERS[self.character_key]

    @property
    def theme(self):
        return THEMES[self.theme_key]

    def combo_window(self) -> float:
        return max(2.8, COMBO_WINDOW + self.difficulty.combo_window_bonus)

    def combo_multiplier(self) -> float:
        if self.combo_chain <= 0:
            return 1.0
        bonus = self.profile.combo_bonus
        return min(4.5, 1.0 + (self.combo_chain - 1) * 0.35 + self.combo_chain * bonus)

    def capture_percent(self) -> float:
        return 100.0 - self.arena.free_ratio() * 100.0

    def capture_progress(self) -> float:
        if self.capture_animation_timer <= 0:
            return 1.0
        return 1.0 - min(1.0, self.capture_animation_timer / CAPTURE_ANIMATION_DURATION)

    def coin_bonus_multiplier(self) -> float:
        return 1.0 + (self.boost.coin_bonus if self.boost else 0.0)

    def active_effect_label(self) -> str:
        active = []
        if self.player.shield_timer > 0:
            active.append(f"Shield {self.player.shield_timer:0.1f}s")
        if self.player.speed_boost_timer > 0:
            active.append(f"Speed {self.player.speed_boost_timer:0.1f}s")
        if self.player.blaster_timer > 0:
            active.append(f"Blaster {self.player.blaster_timer:0.1f}s")
        if self.freeze_timer > 0:
            active.append(f"Freeze {self.freeze_timer:0.1f}s")
        if self.slow_timer > 0:
            active.append(f"Slow {self.slow_timer:0.1f}s")
        if self.boost:
            active.append(f"Boost {self.boost.name}")
        return " | ".join(active) if active else "No active power-up"

    def consume_pending_coins(self) -> int:
        coins = self.pending_coin_reward
        self.pending_coin_reward = 0
        return coins

    def start_level(self, level: int) -> None:
        self.level = level
        self.state = "playing"
        self.capture_flash_timer = 0.0
        self.capture_animation_timer = 0.0
        self.slow_timer = 0.0
        self.freeze_timer = 0.0
        self.projectiles.clear()
        self.powerups.clear()
        self.shot_cooldown = 0.0
        self.toast = ""
        self.toast_timer = 0.0
        self.combo_timer = 0.0
        self.combo_chain = 0
        self.last_capture_points = 0
        self.last_capture_area = 0
        self.last_capture_risk = 0
        self.last_capture_percent = 0.0
        self.draw_exposure_time = 0.0
        self.idle_timer = 0.0
        self.danger_level = 0.0
        self.level_reward_granted = False
        spawn_rate = (POWERUP_SPAWN_INTERVAL - min(4.0, level * 0.42)) * self.difficulty.powerup_rate_multiplier
        self.powerup_spawn_timer = max(4.0, spawn_rate)
        self.arena = Arena(GRID_WIDTH, GRID_HEIGHT)
        self.player = Player(0, GRID_HEIGHT // 2, self.profile)
        self.player.bonus_draw_multiplier = 1.0 + (self.boost.draw_speed_bonus if self.boost else 0.0)
        if self.boost and self.boost.start_shield > 0:
            self.player.give_shield(self.boost.start_shield)
        self.enemies = self._create_level_enemies(level)

    def restart(self) -> None:
        self.score = 0
        self.lives = STARTING_LIVES + self.profile.extra_lives + self.difficulty.extra_lives
        self.best_combo = 1.0
        self.pending_coin_reward = 0
        self.start_level(self.starting_level)

    def set_toast(self, text: str, duration: float = 2.4) -> None:
        self.toast = text
        self.toast_timer = duration

    def _random_enemy_position(self):
        while True:
            cx = random.randint(8, GRID_WIDTH - 9)
            cy = random.randint(8, GRID_HEIGHT - 9)
            if self.arena.is_free(cx, cy):
                return cx * TILE_SIZE + TILE_SIZE / 2, cy * TILE_SIZE + TILE_SIZE / 2

    def _random_free_position(self):
        occupied = {powerup.cell() for powerup in self.powerups}
        player_cell = (self.player.x, self.player.y)
        enemy_cells = {enemy.cell_position() for enemy in self.enemies}
        for _ in range(450):
            cx = random.randint(4, GRID_WIDTH - 5)
            cy = random.randint(4, GRID_HEIGHT - 5)
            if not self.arena.is_free(cx, cy):
                continue
            if (cx, cy) in occupied or (cx, cy) in enemy_cells:
                continue
            if abs(cx - player_cell[0]) + abs(cy - player_cell[1]) < POWERUP_SAFE_RADIUS:
                continue
            return cx, cy
        return None

    def _create_level_enemies(self, level: int):
        enemies = []
        base_speed = (96 + (level - 1) * 10.5) * self.difficulty.enemy_speed_multiplier
        if self.boost and level <= 3:
            base_speed *= 1.0 - self.boost.early_enemy_slow

        if level == 1:
            layout = ["bouncer"]
            base_speed *= 0.82
        elif level == 2:
            layout = ["bouncer", "bouncer"]
            base_speed *= 0.84
        elif level == 3:
            layout = ["bouncer", "hunter"]
            base_speed *= 0.9
        elif level == 4:
            layout = ["bouncer", "hunter", "hunter"]
            base_speed *= 0.96
        elif level == 5:
            layout = ["bouncer", "hunter", "ghost"]
        elif level == 6:
            layout = ["hunter", "hunter", "ghost", "splitter"]
        elif level == 7:
            layout = ["hunter", "ghost", "splitter", "splitter"]
        elif level == 8:
            layout = ["hunter", "ghost", "splitter", "tank"]
        else:
            pool = ["hunter", "ghost", "splitter", "tank", "hunter", "splitter"]
            layout = [pool[index % len(pool)] for index in range(min(2 + level, 7))]

        for index, behavior in enumerate(layout):
            x, y = self._random_enemy_position()
            enemies.append(Enemy(x, y, base_speed, behavior, level=level, leader=index == 0 and level >= 5))
        return enemies

    def _enemy_cells(self):
        return [enemy.cell_position() for enemy in self.enemies]

    def _respawn_after_hit(self) -> None:
        self.player.handle_death(self.arena)
        self.projectiles.clear()
        self.shot_cooldown = 0.0
        self.draw_exposure_time = 0.0
        self.danger_level = 0.0
        for enemy in self.enemies:
            x, y = self._random_enemy_position()
            enemy.reset_position(x, y)
        if self.boost and self.boost.recovery_freeze > 0:
            self.freeze_timer = max(self.freeze_timer, self.boost.recovery_freeze)
        if self.assist_mode:
            self.player.give_shield(max(self.difficulty.recovery_shield, 0.8))
            self.slow_timer = max(self.slow_timer, 1.4)

    def _lose_life(self) -> None:
        player_world_x = self.player.x * TILE_SIZE + TILE_SIZE // 2
        player_world_y = self.player.y * TILE_SIZE + TILE_SIZE // 2
        if self.player.consume_shield():
            self.audio.play("powerup")
            self.shake.add(0.18)
            self.particles.emit_burst(player_world_x, player_world_y, (255, 240, 140), 18, 110)
            self.arena.clear_trail()
            self.player.reset_position()
            self.draw_exposure_time = 0.0
            self.set_toast("Shield absorbed the hit.")
            return

        self.lives -= 1
        self.audio.play("hit")
        self.shake.add(0.75)
        self.particles.emit_burst(player_world_x, player_world_y, (255, 120, 120), 26, 150)
        if self.lives <= 0:
            self.state = "game_over"
            self.player.handle_death(self.arena)
            self.projectiles.clear()
        else:
            self._respawn_after_hit()

    def _spawn_powerup(self) -> None:
        if len(self.powerups) >= MAX_POWERUPS:
            return
        pos = self._random_free_position()
        if pos is None:
            return
        pool = ["freeze", "slow", "shield", "speed_boost", "shield"]
        if self.level >= 2:
            pool.extend(["blaster", "speed_boost"])
        if self.level >= 4:
            pool.extend(["bomb", "freeze"])
        if self.level >= 7:
            pool.extend(["blaster", "bomb"])
        data = POWER_UPS[random.choice(pool)]
        self.powerups.append(PowerUp(data.key, pos[0], pos[1], data.color, data.name, data.icon, data.duration))

    def _apply_powerup(self, powerup: PowerUp) -> None:
        data = POWER_UPS[powerup.key]
        if powerup.key == "freeze":
            self.freeze_timer = max(self.freeze_timer, powerup.duration)
            for enemy in self.enemies:
                enemy.frozen_timer = max(enemy.frozen_timer, powerup.duration)
        elif powerup.key == "slow":
            self.slow_timer = max(self.slow_timer, powerup.duration)
        elif powerup.key == "shield":
            self.player.give_shield(powerup.duration)
        elif powerup.key == "speed_boost":
            self.player.speed_boost_timer = max(self.player.speed_boost_timer, powerup.duration)
        elif powerup.key == "blaster":
            self.player.give_blaster(powerup.duration)
        elif powerup.key == "bomb":
            self._detonate_bomb(powerup)

        self.daily_counters["powerups"] += 1
        self.audio.play("powerup")
        if powerup.key != "bomb":
            self.set_toast(data.award_text or data.name)
        self.particles.emit_burst(
            powerup.x * TILE_SIZE + TILE_SIZE // 2,
            powerup.y * TILE_SIZE + TILE_SIZE // 2,
            powerup.color,
            22,
            105,
        )

    def _detonate_bomb(self, powerup: PowerUp) -> None:
        center_x = powerup.x * TILE_SIZE + TILE_SIZE // 2
        center_y = powerup.y * TILE_SIZE + TILE_SIZE // 2
        affected = 0
        for enemy in self.enemies:
            distance = math.hypot(enemy.x - center_x, enemy.y - center_y)
            if distance > BOMB_RADIUS:
                continue
            enemy.stun(BOMB_STUN_DURATION)
            away_x = enemy.x - center_x
            away_y = enemy.y - center_y
            length = math.hypot(away_x, away_y) or 1.0
            enemy.vx = away_x / length
            enemy.vy = away_y / length
            enemy.target_x = enemy.x + enemy.vx * 120
            enemy.target_y = enemy.y + enemy.vy * 120
            affected += 1

        if affected:
            self.daily_counters["stuns"] += affected
            gained = int((28 + 9 * affected) * self.level * self.difficulty.score_multiplier)
            self.score += gained
            self.daily_counters["score"] += gained
            self.set_toast(f"Bomb disabled {affected} enemy{'ies' if affected != 1 else ''}. +{gained}")
            self.audio.play("stun")
        else:
            self.set_toast("Bomb armed the arena, but no enemies were close.")
        self.shake.add(0.28)
        self.particles.emit_burst(center_x, center_y, powerup.color, 42, 180)

    def _award_captured_powerups(self, captured_cells: list[tuple[int, int]]) -> None:
        if not captured_cells or not self.powerups:
            return
        captured_set = set(captured_cells)
        remaining = []
        for powerup in self.powerups:
            if powerup.cell() in captured_set:
                self._apply_powerup(powerup)
            else:
                remaining.append(powerup)
        self.powerups = remaining

    def fire_projectile(self) -> None:
        if self.state != "playing" or not self.player.can_shoot() or self.shot_cooldown > 0:
            return
        fx, fy = self.player.facing
        if fx == 0 and fy == 0:
            fx = 1
        start_x = self.player.x * TILE_SIZE + TILE_SIZE // 2 + fx * 8
        start_y = self.player.y * TILE_SIZE + TILE_SIZE // 2 + fy * 8
        self.projectiles.append(
            Projectile(
                start_x,
                start_y,
                fx * SHOT_SPEED,
                fy * SHOT_SPEED,
                self.profile.trail,
            )
        )
        self.shot_cooldown = SHOT_COOLDOWN * self.profile.shot_cooldown_multiplier
        self.audio.play("shoot")

    def next_level(self) -> None:
        self.start_level(self.level + 1)

    def _trail_samples(self) -> list[tuple[float, float]]:
        if not self.arena.trail_cells:
            return []
        step = max(1, len(self.arena.trail_cells) // 10)
        samples = self.arena.trail_cells[::step]
        if self.arena.trail_cells[-1] not in samples:
            samples.append(self.arena.trail_cells[-1])
        return [(cell_x * TILE_SIZE + TILE_SIZE / 2, cell_y * TILE_SIZE + TILE_SIZE / 2) for cell_x, cell_y in samples]

    def _enemy_context(self, input_dir) -> dict:
        player_pos = (self.player.x * TILE_SIZE + TILE_SIZE / 2, self.player.y * TILE_SIZE + TILE_SIZE / 2)
        player_idle = input_dir == (0, 0) and not self.player.drawing
        trail_length = len(self.arena.trail_cells)
        pressure = min(0.46, 0.045 + self.level * 0.017 + trail_length * 0.0034 + self.draw_exposure_time * 0.02)
        drawing_reaction = max(0.10, DRAWING_ENEMY_REACTION - self.level * 0.015)
        threat_strength = min(1.0, pressure * 2.25)
        if self.level <= 2:
            pressure *= 0.48
            drawing_reaction += 0.26
            threat_strength *= 0.42
        elif self.level == 3:
            pressure *= 0.68
            drawing_reaction += 0.15
            threat_strength *= 0.62
        elif self.level == 4:
            pressure *= 0.82
            drawing_reaction += 0.08
            threat_strength *= 0.78

        context = {
            "level": self.level,
            "player_pos": player_pos,
            "player_idle": player_idle,
            "idle_reaction": max(0.24, IDLE_ENEMY_REACTION - self.level * 0.03),
            "drawing_reaction": drawing_reaction,
            "pressure": pressure,
            "threat_strength": threat_strength,
            "mode": "idle" if player_idle else "roam",
        }

        if self.player.drawing and self.player.trail_start_cell is not None:
            entry_x = self.player.trail_start_cell[0] * TILE_SIZE + TILE_SIZE / 2
            entry_y = self.player.trail_start_cell[1] * TILE_SIZE + TILE_SIZE / 2
            head_x = self.player.x * TILE_SIZE + TILE_SIZE / 2
            head_y = self.player.y * TILE_SIZE + TILE_SIZE / 2
            predicted_head = (
                head_x + self.player.facing[0] * (22 + min(28, trail_length * 0.5)),
                head_y + self.player.facing[1] * (22 + min(28, trail_length * 0.5)),
            )
            context.update(
                {
                    "mode": "drawing",
                    "trail_entry": (entry_x, entry_y),
                    "trail_head": (head_x, head_y),
                    "predicted_head": predicted_head,
                    "trail_samples": self._trail_samples(),
                }
            )
        return context

    def _update_projectiles(self, dt: float) -> None:
        alive: list[Projectile] = []
        for projectile in self.projectiles:
            if not projectile.update(dt):
                continue

            hit_enemy = None
            for enemy in self.enemies:
                if math.hypot(projectile.x - enemy.x, projectile.y - enemy.y) <= enemy.radius + projectile.radius:
                    hit_enemy = enemy
                    break

            if hit_enemy is not None:
                hit_enemy.stun(SHOT_STUN_DURATION)
                self.daily_counters["stuns"] += 1
                self.audio.play("stun")
                gained = int(22 * self.level * self.difficulty.score_multiplier)
                self.score += gained
                self.daily_counters["score"] += gained
                self.particles.emit_burst(projectile.x, projectile.y, projectile.color, 12, 80)
                continue

            alive.append(projectile)
        self.projectiles = alive

    def _capture_score(self, captured_count: int, trail_length: int) -> int:
        area_percent = (captured_count / self.arena.initial_free_cells) * 100.0
        score_bonus = 1.0 + (self.boost.score_bonus if self.boost else 0.0)
        area_score = (captured_count * CAPTURE_BASE_SCORE + area_percent * CAPTURE_AREA_BONUS) * self.level * self.profile.capture_bonus
        risk_bonus = trail_length * CAPTURE_TRAIL_BONUS * (0.75 + min(1.7, self.draw_exposure_time * 0.35)) * self.profile.trail_bonus
        combo_mult = self.combo_multiplier()
        total = max(25, int((area_score + risk_bonus) * combo_mult * self.difficulty.score_multiplier * score_bonus))
        self.last_capture_area = int(area_score)
        self.last_capture_risk = int(risk_bonus)
        self.last_capture_points = total
        self.last_capture_percent = area_percent
        self.daily_counters["big_capture"] = max(self.daily_counters["big_capture"], area_percent)
        return total

    def _grant_level_reward(self) -> None:
        if self.level_reward_granted:
            return
        self.level_reward_granted = True
        reward = 12 + self.level * 4
        reward = int(round(reward * self.coin_bonus_multiplier()))
        self.pending_coin_reward += reward
        self.daily_counters["levels"] += 1
        self.set_toast(f"Level clear reward +{reward} coin.")

    def _update_danger_feedback(self) -> None:
        if not self.enemies:
            self.danger_level = 0.0
            return
        player_x = self.player.x * TILE_SIZE + TILE_SIZE / 2
        player_y = self.player.y * TILE_SIZE + TILE_SIZE / 2
        nearest = min(math.hypot(enemy.x - player_x, enemy.y - player_y) - enemy.radius for enemy in self.enemies)
        ratio = 1.0 - min(1.0, max(0.0, nearest) / DANGER_RADIUS)
        self.danger_level = ratio if self.player.drawing else ratio * 0.35
        if self.player.drawing and self.danger_level > 0.78:
            self.shake.add(0.03)

    def update(self, dt: float, input_dir):
        self.capture_flash_timer = max(0.0, self.capture_flash_timer - dt)
        self.capture_animation_timer = max(0.0, self.capture_animation_timer - dt)
        self.slow_timer = max(0.0, self.slow_timer - dt)
        self.freeze_timer = max(0.0, self.freeze_timer - dt)
        self.shot_cooldown = max(0.0, self.shot_cooldown - dt)
        self.toast_timer = max(0.0, self.toast_timer - dt)
        self.combo_timer = max(0.0, self.combo_timer - dt)
        if self.combo_timer <= 0:
            self.combo_chain = 0
        if self.toast_timer <= 0:
            self.toast = ""

        self.powerups = [powerup for powerup in self.powerups if powerup.update(dt)]
        self._update_projectiles(dt)
        if self.state != "playing":
            return

        if input_dir == (0, 0) and not self.player.drawing:
            self.idle_timer += dt
        else:
            self.idle_timer = 0.0

        self.powerup_spawn_timer -= dt
        if self.powerup_spawn_timer <= 0:
            spawn_rate = (POWERUP_SPAWN_INTERVAL - min(4.0, self.level * 0.42)) * self.difficulty.powerup_rate_multiplier
            self.powerup_spawn_timer = max(4.0, spawn_rate)
            self._spawn_powerup()

        result = self.player.update(dt, self.arena, input_dir)
        if self.player.drawing:
            self.draw_exposure_time += dt
            if self.last_move_sound > 0:
                self.last_move_sound -= dt
            if input_dir != (0, 0) and self.last_move_sound <= 0:
                self.audio.play("move")
                self.last_move_sound = 0.10
        else:
            self.draw_exposure_time = 0.0
            self.last_move_sound = max(0.0, self.last_move_sound - dt)

        if result == "dead":
            self._lose_life()
            return

        if result == "captured":
            trail_snapshot = list(self.arena.trail_cells)
            trail_length = len(trail_snapshot)
            captured_count, captured_cells = self.arena.finalize_capture(self._enemy_cells())

            if captured_count > 0:
                if self.combo_timer > 0:
                    self.combo_chain += 1
                else:
                    self.combo_chain = 1
                self.combo_timer = self.combo_window()
                self.best_combo = max(self.best_combo, self.combo_multiplier())
                capture_points = self._capture_score(captured_count, trail_length)
                self.score += capture_points
                self.daily_counters["score"] += capture_points
                self.daily_counters["captures"] += 1
            else:
                self.last_capture_points = 0
                self.last_capture_area = 0
                self.last_capture_risk = 0
                self.last_capture_percent = 0.0

            self.capture_flash_timer = 0.5
            self.capture_animation_timer = CAPTURE_ANIMATION_DURATION
            self.audio.play("capture")
            self.shake.add(0.18)
            self._award_captured_powerups(captured_cells)
            if trail_snapshot:
                trail_points = [
                    (cell_x * TILE_SIZE + TILE_SIZE / 2, cell_y * TILE_SIZE + TILE_SIZE / 2)
                    for cell_x, cell_y in trail_snapshot[:: max(1, len(trail_snapshot) // 18)]
                ]
                self.particles.emit_line(trail_points, self.theme.trail_glow, density=2, speed=55)
            if captured_cells:
                sample = captured_cells[len(captured_cells) // 2]
                self.particles.emit_burst(
                    sample[0] * TILE_SIZE + TILE_SIZE // 2,
                    sample[1] * TILE_SIZE + TILE_SIZE // 2,
                    self.theme.particle,
                    32,
                    140,
                )
                self.set_toast(
                    f"+{self.last_capture_points} area {self.last_capture_area} risk {self.last_capture_risk} combo x{self.combo_multiplier():0.2f}"
                )
            else:
                self.set_toast("Loop closed. No territory trapped.")

            self.draw_exposure_time = 0.0
            if self.arena.free_ratio() <= TARGET_FREE_RATIO:
                self.state = "level_clear"
                self.audio.play("level")
                self._grant_level_reward()
                return

        slow_factor = 0.56 if self.slow_timer > 0 else 1.0
        if self.level <= 2:
            slow_factor *= 0.94
        context = self._enemy_context(input_dir)
        for enemy in self.enemies:
            if self.freeze_timer > 0:
                enemy.frozen_timer = max(enemy.frozen_timer, self.freeze_timer)
            enemy.update(dt, self.arena, slow_factor, context, self.theme.enemy_speed_scale)
            if self.player.drawing and enemy.touches_trail(self.arena):
                self._lose_life()
                return

        self._update_danger_feedback()
        if self.arena.free_ratio() <= TARGET_FREE_RATIO:
            self.state = "level_clear"
            self.audio.play("level")
            self._grant_level_reward()

    def flash_ratio(self) -> float:
        return min(1.0, self.capture_flash_timer / 0.5) if self.capture_flash_timer > 0 else 0.0

    def pulse(self) -> float:
        return (math.sin(pygame.time.get_ticks() * 0.008) + 1.0) * 0.5
