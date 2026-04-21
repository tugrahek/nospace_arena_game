from __future__ import annotations

from datetime import date
import random

import pygame

from .audio import AudioManager
from .config import FPS, GAME_TITLE, SCREEN_HEIGHT, SCREEN_WIDTH, SettingsManager
from .content import BOOSTS, CHARACTERS, DIFFICULTIES, THEMES
from .effects import ParticleSystem, ScreenShake, ScreenTransition
from .gameplay import GameSession
from .ui import (
    FontSet,
    Menu,
    draw_boost_info,
    draw_center_message,
    draw_daily_missions,
    draw_danger_overlay,
    draw_how_to_play,
    draw_hud,
    draw_level_select,
    draw_menu,
    draw_notice,
    draw_pause_overlay,
    draw_selection_panel,
    draw_settings_panel,
    draw_store_panel,
    draw_themed_background,
)


class NoSpaceArenaApp:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption(GAME_TITLE)
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.frame = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.clock = pygame.time.Clock()
        self.fonts = FontSet()
        self.settings = SettingsManager()
        self._ensure_meta_defaults()
        self.audio = AudioManager(self.settings.data)
        self.particles = ParticleSystem()
        self.transition = ScreenTransition()
        self.shake = ScreenShake()
        self.running = True
        self.tick = 0.0
        self.notice = ""
        self.notice_timer = 0.0
        self.daily_snapshot: dict[str, float] = {}

        self.main_menu = Menu(
            "Main Menu",
            [
                "Start Game",
                "Level Select",
                "Character Select",
                "Arena Select",
                "Daily Missions",
                "Store",
                "Boost Info",
                "Settings",
                "How to Play",
                "Quit",
            ],
        )
        self.settings_menu = Menu("Settings", ["Difficulty", "Assist Mode", "Music", "Sound", "Volume", "Screen Shake", "Back"])
        self.daily_menu = Menu("Daily Missions", ["Mission 1", "Mission 2", "Mission 3"])
        self.store_categories = ["Characters", "Arenas", "Boosts"]
        self.store_category_index = 0
        self.store_indices = {category: 0 for category in self.store_categories}
        self.boost_info_index = 0
        self.selected_level = int(self.settings.data.get("selected_level", 1))
        self.state = "menu"
        self.session = None

        self._refresh_daily_missions()
        self._refresh_owned_lists()

    def _ensure_meta_defaults(self) -> None:
        data = self.settings.data
        changed = False
        defaults = {
            "selected_level": 1,
            "difficulty": "arcade",
            "assist_mode": True,
            "high_score": 0,
            "best_level": 1,
            "coins": 0,
            "unlocked_characters": [key for key, value in CHARACTERS.items() if value.unlocked_by_default],
            "unlocked_arenas": [key for key, value in THEMES.items() if value.unlocked_by_default],
            "unlocked_boosts": [],
            "equipped_boost": "",
            "level_scores": {},
            "daily_missions": {"date": "", "missions": []},
        }
        for key, value in defaults.items():
            if key not in data:
                data[key] = value
                changed = True

        if data["difficulty"] not in DIFFICULTIES:
            data["difficulty"] = "arcade"
            changed = True
        if data["character"] not in CHARACTERS:
            data["character"] = "spark"
            changed = True
        if data["arena_theme"] not in THEMES:
            data["arena_theme"] = "neon"
            changed = True
        if data.get("equipped_boost", "") not in BOOSTS:
            data["equipped_boost"] = ""
            changed = True
        data["unlocked_characters"] = sorted(set(data.get("unlocked_characters", [])) | {key for key, value in CHARACTERS.items() if value.unlocked_by_default})
        data["unlocked_arenas"] = sorted(set(data.get("unlocked_arenas", [])) | {key for key, value in THEMES.items() if value.unlocked_by_default})
        data["unlocked_boosts"] = list(dict.fromkeys(data.get("unlocked_boosts", [])))
        if not isinstance(data.get("level_scores"), dict):
            data["level_scores"] = {}
            changed = True
        if not isinstance(data.get("daily_missions"), dict):
            data["daily_missions"] = {"date": "", "missions": []}
            changed = True
        if changed:
            self.settings.save()

    def _refresh_owned_lists(self) -> None:
        unlocked_characters = [key for key in CHARACTERS if key in self.settings.data["unlocked_characters"]]
        unlocked_arenas = [key for key in THEMES if key in self.settings.data["unlocked_arenas"]]
        if self.settings.data["character"] not in unlocked_characters:
            self.settings.data["character"] = unlocked_characters[0]
        if self.settings.data["arena_theme"] not in unlocked_arenas:
            self.settings.data["arena_theme"] = unlocked_arenas[0]
        self.character_keys = unlocked_characters
        self.theme_keys = unlocked_arenas
        self.character_index = self.character_keys.index(self.settings.data["character"])
        self.theme_index = self.theme_keys.index(self.settings.data["arena_theme"])
        self.settings.save()

    def _set_notice(self, text: str, duration: float = 2.8) -> None:
        self.notice = text
        self.notice_timer = duration

    def _today_key(self) -> str:
        return date.today().isoformat()

    def _mission_templates(self) -> list[dict]:
        return [
            {"metric": "score", "mode": "sum", "target": 3500, "reward": 65, "title": "Point Break", "description": "Earn 3500 total score today."},
            {"metric": "captures", "mode": "sum", "target": 8, "reward": 45, "title": "Claim Chain", "description": "Complete 8 successful territory captures."},
            {"metric": "powerups", "mode": "sum", "target": 4, "reward": 50, "title": "Treasure Route", "description": "Capture 4 power-up capsules."},
            {"metric": "stuns", "mode": "sum", "target": 6, "reward": 55, "title": "Shock Duty", "description": "Stun 6 enemies with the Blaster."},
            {"metric": "levels", "mode": "sum", "target": 2, "reward": 80, "title": "Clear Path", "description": "Clear 2 levels."},
            {"metric": "big_capture", "mode": "max", "target": 9, "reward": 60, "title": "Huge Slice", "description": "Capture at least 9 percent in a single close."},
        ]

    def _refresh_daily_missions(self) -> None:
        today_key = self._today_key()
        daily = self.settings.data.get("daily_missions", {"date": "", "missions": []})
        if daily.get("date") == today_key and daily.get("missions"):
            return
        mission_rng = random.Random(today_key)
        selected = mission_rng.sample(self._mission_templates(), 3)
        self.settings.data["daily_missions"] = {
            "date": today_key,
            "missions": [
                {
                    "metric": template["metric"],
                    "mode": template["mode"],
                    "target": template["target"],
                    "reward": template["reward"],
                    "title": template["title"],
                    "description": template["description"],
                    "progress": 0.0,
                    "completed": False,
                    "claimed": False,
                }
                for template in selected
            ],
        }
        self.settings.save()

    def _update_daily_progress(self) -> None:
        if self.session is None:
            return
        missions = self.settings.data["daily_missions"]["missions"]
        counters = self.session.daily_counters
        changed = False
        for mission in missions:
            current_value = float(counters.get(mission["metric"], 0.0))
            if mission["mode"] == "sum":
                previous = self.daily_snapshot.get(mission["metric"], 0.0)
                delta = max(0.0, current_value - previous)
                if delta > 0:
                    mission["progress"] = min(mission["target"], mission["progress"] + delta)
                    changed = True
                self.daily_snapshot[mission["metric"]] = current_value
            else:
                if current_value > mission["progress"]:
                    mission["progress"] = min(mission["target"], current_value)
                    changed = True
                self.daily_snapshot[mission["metric"]] = max(self.daily_snapshot.get(mission["metric"], 0.0), current_value)
            mission["completed"] = mission["progress"] >= mission["target"]
        if changed:
            self.settings.save()

    def _claim_daily_mission(self) -> None:
        missions = self.settings.data["daily_missions"]["missions"]
        if not missions:
            return
        mission = missions[self.daily_menu.index]
        if mission["completed"] and not mission["claimed"]:
            mission["claimed"] = True
            self.settings.data["coins"] += int(mission["reward"])
            self.settings.save()
            self._set_notice(f"{mission['title']} tamamlandi. +{mission['reward']} coin.")
        elif mission["claimed"]:
            self._set_notice("This mission reward has already been claimed.")
        else:
            self._set_notice("This mission is not complete yet.")

    def current_theme(self):
        if self.session is not None:
            return THEMES[self.session.theme_key]
        return THEMES[self.settings.data["arena_theme"]]

    def start_game(self, starting_level: int | None = None):
        level = starting_level or self.selected_level
        unlocked_limit = max(1, int(self.settings.data.get("best_level", 1)))
        if level > unlocked_limit:
            level = unlocked_limit
        self.selected_level = level
        self.settings.data["selected_level"] = level
        self.settings.save()
        self.daily_snapshot = {}
        self.session = GameSession(
            self.audio,
            self.particles,
            self.shake,
            self.settings.data["character"],
            self.settings.data["arena_theme"],
            self.settings.data["difficulty"],
            self.settings.data["assist_mode"],
            self.settings.data.get("equipped_boost", ""),
            level,
        )
        self.state = "playing"
        self.transition.trigger()

    def _change_character(self, delta: int):
        self.character_index = (self.character_index + delta) % len(self.character_keys)
        self.settings.set("character", self.character_keys[self.character_index])

    def _change_theme(self, delta: int):
        self.theme_index = (self.theme_index + delta) % len(self.theme_keys)
        self.settings.set("arena_theme", self.theme_keys[self.theme_index])

    def _change_level(self, delta: int):
        self.selected_level = max(1, min(10, self.selected_level + delta))
        self.settings.set("selected_level", self.selected_level)

    def _handle_global_shortcuts(self, event):
        if event.type != pygame.KEYDOWN:
            return
        if event.key == pygame.K_m:
            self.settings.set("music_enabled", not self.settings.data["music_enabled"])
        elif event.key == pygame.K_n:
            self.settings.set("sound_enabled", not self.settings.data["sound_enabled"])
        elif event.key == pygame.K_LEFTBRACKET:
            self.audio.set_volume(self.settings.data["volume"] - 0.05)
            self.settings.save()
        elif event.key == pygame.K_RIGHTBRACKET:
            self.audio.set_volume(self.settings.data["volume"] + 0.05)
            self.settings.save()

    def _settings_lines(self) -> list[str]:
        return [
            f"Difficulty: {DIFFICULTIES[self.settings.data['difficulty']].name}",
            f"Assist Mode: {'On' if self.settings.data['assist_mode'] else 'Off'}",
            f"Music: {'On' if self.settings.data['music_enabled'] else 'Off'}",
            f"Sound: {'On' if self.settings.data['sound_enabled'] else 'Off'}",
            f"Volume: {int(self.settings.data['volume'] * 100):d}%",
            f"Screen Shake: {'On' if self.settings.data.get('screen_shake', True) else 'Off'}",
            "Back",
        ]

    def _adjust_setting(self, delta: int = 0, confirm: bool = False) -> None:
        choice = self.settings_menu.selected()
        if choice == "Difficulty":
            keys = list(DIFFICULTIES.keys())
            current = keys.index(self.settings.data["difficulty"])
            step = 1 if delta == 0 else delta
            self.settings.set("difficulty", keys[(current + step) % len(keys)])
        elif choice == "Assist Mode":
            self.settings.set("assist_mode", not self.settings.data["assist_mode"])
        elif choice == "Music":
            self.settings.set("music_enabled", not self.settings.data["music_enabled"])
        elif choice == "Sound":
            self.settings.set("sound_enabled", not self.settings.data["sound_enabled"])
        elif choice == "Volume":
            if delta != 0:
                self.audio.set_volume(self.settings.data["volume"] + 0.05 * delta)
                self.settings.save()
        elif choice == "Screen Shake":
            self.settings.set("screen_shake", not self.settings.data.get("screen_shake", True))
        elif choice == "Back" and confirm:
            self.state = "menu"

    def _store_items(self, category_name: str) -> list[dict]:
        if category_name == "Characters":
            return [
                {
                    "category": category_name,
                    "key": key,
                    "name": value.name,
                    "description": value.description,
                    "cost": value.cost,
                    "owned": key in self.settings.data["unlocked_characters"],
                    "details": (
                        f"Move speed x{value.speed_multiplier:.2f}",
                        f"Draw speed x{value.drawing_multiplier:.2f}",
                        f"Capture bonus x{value.capture_bonus:.2f}",
                        f"Risk bonus x{value.trail_bonus:.2f}",
                    ),
                }
                for key, value in CHARACTERS.items()
            ]
        if category_name == "Arenas":
            return [
                {
                    "category": category_name,
                    "key": key,
                    "name": value.name,
                    "description": value.description,
                    "cost": value.cost,
                    "owned": key in self.settings.data["unlocked_arenas"],
                    "details": (
                        f"Pattern {value.pattern}",
                        f"Enemy speed x{value.enemy_speed_scale:.2f}",
                        f"Trail glow {value.trail_glow}",
                        f"Danger tint {value.danger}",
                    ),
                }
                for key, value in THEMES.items()
            ]
        return [
            {
                "category": category_name,
                "key": key,
                "name": value.name,
                "description": value.description,
                "cost": value.cost,
                "owned": key in self.settings.data["unlocked_boosts"],
                "details": value.details,
            }
            for key, value in BOOSTS.items()
        ]

    def _purchase_or_equip_store_item(self):
        category = self.store_categories[self.store_category_index]
        items = self._store_items(category)
        item = items[self.store_indices[category]]
        key = item["key"]

        if item["owned"]:
            if category == "Characters":
                self.settings.set("character", key)
                self._refresh_owned_lists()
                self._set_notice(f"{item['name']} selected.")
            elif category == "Arenas":
                self.settings.set("arena_theme", key)
                self._refresh_owned_lists()
                self._set_notice(f"{item['name']} selected.")
            else:
                equipped = self.settings.data.get("equipped_boost", "")
                new_value = "" if equipped == key else key
                self.settings.set("equipped_boost", new_value)
                self._set_notice(f"{item['name']} {'unequipped' if equipped == key else 'equipped'}.")
            return

        if self.settings.data["coins"] < item["cost"]:
            self._set_notice("Not enough coins.")
            return

        self.settings.data["coins"] -= item["cost"]
        if category == "Characters":
            self.settings.data["unlocked_characters"].append(key)
            self.settings.data["character"] = key
        elif category == "Arenas":
            self.settings.data["unlocked_arenas"].append(key)
            self.settings.data["arena_theme"] = key
        else:
            self.settings.data["unlocked_boosts"].append(key)
            self.settings.data["equipped_boost"] = key
        self.settings.save()
        self._refresh_owned_lists()
        self._set_notice(f"{item['name']} unlocked.")

    def _change_store_category(self, delta: int):
        self.store_category_index = (self.store_category_index + delta) % len(self.store_categories)

    def _level_is_unlocked(self, level: int) -> bool:
        return level <= max(1, int(self.settings.data.get("best_level", 1)))

    def _sync_progress(self):
        if self.session is None:
            return
        changed = False

        reward = self.session.consume_pending_coins()
        if reward > 0:
            self.settings.data["coins"] += reward
            changed = True

        if self.session.score > self.settings.data.get("high_score", 0):
            self.settings.data["high_score"] = self.session.score
            changed = True

        level_key = str(self.session.level)
        level_scores = self.settings.data.get("level_scores", {})
        previous_level_score = int(level_scores.get(level_key, 0))
        if self.session.score > previous_level_score:
            level_scores[level_key] = self.session.score
            self.settings.data["level_scores"] = level_scores
            changed = True

        if self.session.state == "level_clear":
            next_unlocked = min(10, self.session.level + 1)
            if next_unlocked > int(self.settings.data.get("best_level", 1)):
                self.settings.data["best_level"] = next_unlocked
                changed = True

        self._update_daily_progress()
        if changed:
            self.settings.save()

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                continue

            self._handle_global_shortcuts(event)
            if event.type != pygame.KEYDOWN:
                continue

            if self.state == "menu":
                if event.key in (pygame.K_UP, pygame.K_w):
                    self.main_menu.move(-1)
                    self.audio.play("menu")
                elif event.key in (pygame.K_DOWN, pygame.K_s):
                    self.main_menu.move(1)
                    self.audio.play("menu")
                elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    choice = self.main_menu.selected()
                    self.audio.play("menu")
                    if choice == "Start Game":
                        self.start_game()
                    elif choice == "Level Select":
                        self.state = "level_select"
                    elif choice == "Character Select":
                        self.state = "character_select"
                    elif choice == "Arena Select":
                        self.state = "arena_select"
                    elif choice == "Daily Missions":
                        self.state = "daily_missions"
                    elif choice == "Store":
                        self.state = "store"
                    elif choice == "Boost Info":
                        self.state = "boost_info"
                    elif choice == "Settings":
                        self.state = "settings"
                    elif choice == "How to Play":
                        self.state = "how_to_play"
                    elif choice == "Quit":
                        self.running = False
                elif event.key == pygame.K_ESCAPE:
                    self.running = False

            elif self.state == "character_select":
                if event.key in (pygame.K_UP, pygame.K_w, pygame.K_LEFT, pygame.K_a):
                    self._change_character(-1)
                    self.audio.play("menu")
                elif event.key in (pygame.K_DOWN, pygame.K_s, pygame.K_RIGHT, pygame.K_d):
                    self._change_character(1)
                    self.audio.play("menu")
                elif event.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_ESCAPE):
                    self.state = "menu"
                    self.audio.play("menu")

            elif self.state == "arena_select":
                if event.key in (pygame.K_UP, pygame.K_w, pygame.K_LEFT, pygame.K_a):
                    self._change_theme(-1)
                    self.audio.play("menu")
                elif event.key in (pygame.K_DOWN, pygame.K_s, pygame.K_RIGHT, pygame.K_d):
                    self._change_theme(1)
                    self.audio.play("menu")
                elif event.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_ESCAPE):
                    self.state = "menu"
                    self.audio.play("menu")

            elif self.state == "level_select":
                if event.key in (pygame.K_UP, pygame.K_w, pygame.K_LEFT, pygame.K_a):
                    self._change_level(-1)
                    self.audio.play("menu")
                elif event.key in (pygame.K_DOWN, pygame.K_s, pygame.K_RIGHT, pygame.K_d):
                    self._change_level(1)
                    self.audio.play("menu")
                elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    if self._level_is_unlocked(self.selected_level):
                        self.start_game(self.selected_level)
                    else:
                        self._set_notice("This level is still locked.")
                    self.audio.play("menu")
                elif event.key == pygame.K_ESCAPE:
                    self.state = "menu"
                    self.audio.play("menu")

            elif self.state == "daily_missions":
                if event.key in (pygame.K_UP, pygame.K_w):
                    self.daily_menu.move(-1)
                    self.audio.play("menu")
                elif event.key in (pygame.K_DOWN, pygame.K_s):
                    self.daily_menu.move(1)
                    self.audio.play("menu")
                elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    self._claim_daily_mission()
                    self.audio.play("menu")
                elif event.key == pygame.K_ESCAPE:
                    self.state = "menu"
                    self.audio.play("menu")

            elif self.state == "store":
                category = self.store_categories[self.store_category_index]
                items = self._store_items(category)
                if event.key in (pygame.K_LEFT, pygame.K_a):
                    self._change_store_category(-1)
                    self.audio.play("menu")
                elif event.key in (pygame.K_RIGHT, pygame.K_d):
                    self._change_store_category(1)
                    self.audio.play("menu")
                elif event.key in (pygame.K_UP, pygame.K_w):
                    self.store_indices[category] = (self.store_indices[category] - 1) % len(items)
                    self.audio.play("menu")
                elif event.key in (pygame.K_DOWN, pygame.K_s):
                    self.store_indices[category] = (self.store_indices[category] + 1) % len(items)
                    self.audio.play("menu")
                elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    self._purchase_or_equip_store_item()
                    self.audio.play("menu")
                elif event.key == pygame.K_ESCAPE:
                    self.state = "menu"
                    self.audio.play("menu")

            elif self.state == "boost_info":
                boost_keys = list(BOOSTS.keys())
                if event.key in (pygame.K_UP, pygame.K_w, pygame.K_LEFT, pygame.K_a):
                    self.boost_info_index = (self.boost_info_index - 1) % len(boost_keys)
                    self.audio.play("menu")
                elif event.key in (pygame.K_DOWN, pygame.K_s, pygame.K_RIGHT, pygame.K_d):
                    self.boost_info_index = (self.boost_info_index + 1) % len(boost_keys)
                    self.audio.play("menu")
                elif event.key == pygame.K_ESCAPE:
                    self.state = "menu"
                    self.audio.play("menu")

            elif self.state == "settings":
                if event.key in (pygame.K_UP, pygame.K_w):
                    self.settings_menu.move(-1)
                    self.audio.play("menu")
                elif event.key in (pygame.K_DOWN, pygame.K_s):
                    self.settings_menu.move(1)
                    self.audio.play("menu")
                elif event.key in (pygame.K_LEFT, pygame.K_a):
                    self._adjust_setting(-1)
                    self.audio.play("menu")
                elif event.key in (pygame.K_RIGHT, pygame.K_d):
                    self._adjust_setting(1)
                    self.audio.play("menu")
                elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    self._adjust_setting(confirm=True)
                    self.audio.play("menu")
                elif event.key == pygame.K_ESCAPE:
                    self.state = "menu"
                    self.audio.play("menu")

            elif self.state == "how_to_play":
                if event.key in (pygame.K_ESCAPE, pygame.K_RETURN, pygame.K_SPACE):
                    self.state = "menu"
                    self.audio.play("menu")

            elif self.state == "playing" and self.session is not None:
                if event.key == pygame.K_p:
                    self.state = "paused"
                    self.audio.play("menu")
                elif event.key == pygame.K_ESCAPE:
                    self.state = "menu"
                    self.session = None
                    self.transition.trigger()
                elif self.session.state == "playing" and event.key in (pygame.K_SPACE, pygame.K_LCTRL, pygame.K_RCTRL):
                    self.session.fire_projectile()
                elif self.session.state == "level_clear" and event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    self.session.next_level()
                elif self.session.state == "game_over" and event.key == pygame.K_r:
                    self.daily_snapshot = {}
                    self.session.restart()

            elif self.state == "paused" and self.session is not None:
                if event.key in (pygame.K_p, pygame.K_RETURN, pygame.K_SPACE):
                    self.state = "playing"
                    self.audio.play("menu")
                elif event.key == pygame.K_r:
                    self.daily_snapshot = {}
                    self.session.restart()
                    self.state = "playing"
                    self.audio.play("menu")
                elif event.key == pygame.K_ESCAPE:
                    self.state = "menu"
                    self.session = None
                    self.transition.trigger()
                    self.audio.play("menu")

    def input_dir(self):
        keys = pygame.key.get_pressed()
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            return -1, 0
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            return 1, 0
        if keys[pygame.K_UP] or keys[pygame.K_w]:
            return 0, -1
        if keys[pygame.K_DOWN] or keys[pygame.K_s]:
            return 0, 1
        return 0, 0

    def update(self, dt: float):
        self.tick += dt
        self.transition.update(dt)
        self.audio.update_music(dt)
        self.particles.update(dt)
        self.shake.update(dt, self.settings.data.get("screen_shake", True))
        self.notice_timer = max(0.0, self.notice_timer - dt)
        if self.notice_timer <= 0:
            self.notice = ""
        self._refresh_daily_missions()
        if self.state == "playing" and self.session is not None:
            self.session.update(dt, self.input_dir())
            self._sync_progress()
        elif self.state == "paused" and self.session is not None:
            self._sync_progress()

    def draw_playing(self, surface: pygame.Surface):
        theme = THEMES[self.session.theme_key]
        draw_themed_background(surface, theme, self.tick)
        self.session.arena.draw(
            surface,
            theme,
            self.session.pulse(),
            self.session.flash_ratio(),
            self.session.capture_progress(),
        )
        for powerup in self.session.powerups:
            powerup.draw(surface)
        for projectile in self.session.projectiles:
            projectile.draw(surface)
        for enemy in self.session.enemies:
            enemy.draw(surface)
        self.session.player.draw(surface, self.session.pulse(), self.session.danger_level)
        self.particles.draw(surface)
        draw_danger_overlay(surface, theme, self.session.danger_level)
        draw_hud(surface, self.fonts, theme, self.session, self.settings.data["coins"])

        if self.session.state == "level_clear":
            draw_center_message(
                surface,
                self.fonts,
                theme,
                "Level Cleared",
                [
                    f"Captured territory reached {self.session.capture_percent():.1f} percent.",
                    "Press Enter or Space for the next level.",
                ],
            )
        elif self.session.state == "game_over":
            draw_center_message(
                surface,
                self.fonts,
                theme,
                "Game Over",
                [
                    f"Final score {self.session.score} with a best combo x{self.session.best_combo:.2f}.",
                    "Press R to restart, or Escape for the menu.",
                ],
            )

    def draw(self):
        theme = self.current_theme()
        draw_themed_background(self.frame, theme, self.tick)

        if self.state == "menu":
            footer = (
                f"Coins {self.settings.data['coins']} | High Score {self.settings.data['high_score']} | "
                f"Best Level {self.settings.data['best_level']} | Boost "
                f"{BOOSTS[self.settings.data['equipped_boost']].name if self.settings.data.get('equipped_boost') in BOOSTS else 'None'}"
            )
            draw_menu(
                self.frame,
                self.fonts,
                self.main_menu,
                theme,
                footer,
            )
        elif self.state == "character_select":
            draw_selection_panel(
                self.frame,
                self.fonts,
                "Character Select",
                [CHARACTERS[key] for key in self.character_keys],
                self.character_index,
                theme,
                "Unlocked pilots stay available here. New pilots can be unlocked from the Store.",
            )
        elif self.state == "arena_select":
            draw_selection_panel(
                self.frame,
                self.fonts,
                "Arena Select",
                [THEMES[key] for key in self.theme_keys],
                self.theme_index,
                theme,
                "Unlocked arenas stay available here. New arenas can be unlocked from the Store.",
            )
        elif self.state == "level_select":
            draw_level_select(self.frame, self.fonts, theme, self.selected_level, self.settings.data["best_level"], self.settings.data["level_scores"])
        elif self.state == "daily_missions":
            daily = self.settings.data["daily_missions"]
            draw_daily_missions(self.frame, self.fonts, theme, daily["missions"], self.daily_menu.index, self.settings.data["coins"], daily["date"])
        elif self.state == "store":
            category = self.store_categories[self.store_category_index]
            items = self._store_items(category)
            draw_store_panel(
                self.frame,
                self.fonts,
                theme,
                category,
                items,
                self.store_indices[category],
                self.settings.data["coins"],
                self.settings.data.get("equipped_boost", ""),
            )
        elif self.state == "boost_info":
            draw_boost_info(
                self.frame,
                self.fonts,
                theme,
                list(BOOSTS.keys()),
                self.boost_info_index,
                set(self.settings.data["unlocked_boosts"]),
                self.settings.data.get("equipped_boost", ""),
            )
        elif self.state == "settings":
            draw_settings_panel(self.frame, self.fonts, self.settings_menu, self._settings_lines(), theme)
        elif self.state == "how_to_play":
            draw_how_to_play(self.frame, self.fonts, theme)
        elif self.state == "playing" and self.session is not None:
            self.draw_playing(self.frame)
        elif self.state == "paused" and self.session is not None:
            self.draw_playing(self.frame)
            draw_pause_overlay(self.frame, self.fonts, theme, self.session)

        draw_notice(self.frame, self.fonts, theme, self.notice)
        self.shake.apply(self.frame, self.screen)
        self.transition.draw(self.screen)
        pygame.display.flip()

    def run(self):
        while self.running:
            dt = self.clock.tick(FPS) / 1000.0
            self.handle_events()
            self.update(dt)
            self.draw()
        pygame.quit()
