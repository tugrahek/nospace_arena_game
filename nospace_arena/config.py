from __future__ import annotations

import json
from pathlib import Path

TILE_SIZE = 8
GRID_WIDTH = 100
GRID_HEIGHT = 70
HUD_HEIGHT = 136
SCREEN_WIDTH = GRID_WIDTH * TILE_SIZE
SCREEN_HEIGHT = GRID_HEIGHT * TILE_SIZE + HUD_HEIGHT
FPS = 60
GAME_TITLE = "NoSpace: Arena"

FREE = 0
SOLID = 1
TRAIL = 2

TARGET_FREE_RATIO = 0.20
BASE_PLAYER_STEPS_PER_SECOND = 18
STARTING_LIVES = 3
POWERUP_SPAWN_INTERVAL = 10.0
MAX_POWERUPS = 3
SHOT_SPEED = 360.0
SHOT_LIFETIME = 1.2
SHOT_COOLDOWN = 0.24
SHOT_STUN_DURATION = 2.4
BOMB_RADIUS = 118.0
BOMB_STUN_DURATION = 3.5
COMBO_WINDOW = 5.5
CAPTURE_ANIMATION_DURATION = 0.65
CAPTURE_BASE_SCORE = 6
CAPTURE_AREA_BONUS = 28
CAPTURE_TRAIL_BONUS = 8
DANGER_RADIUS = 120.0
POWERUP_SAFE_RADIUS = 7
IDLE_ENEMY_REACTION = 0.92
DRAWING_ENEMY_REACTION = 0.42

CONFIG_PATH = Path(__file__).resolve().parent.parent / "nospace_arena_settings.json"

DEFAULT_SETTINGS = {
    "character": "spark",
    "arena_theme": "neon",
    "selected_level": 1,
    "difficulty": "arcade",
    "assist_mode": True,
    "sound_enabled": True,
    "music_enabled": True,
    "volume": 0.45,
    "screen_shake": True,
    "high_score": 0,
    "best_level": 1,
    "coins": 0,
    "unlocked_characters": ["spark"],
    "unlocked_arenas": ["neon"],
    "unlocked_boosts": [],
    "equipped_boost": "",
    "level_scores": {},
    "daily_missions": {"date": "", "missions": []},
}


class SettingsManager:
    def __init__(self, path: Path = CONFIG_PATH):
        self.path = path
        self.data = DEFAULT_SETTINGS.copy()
        self.load()

    def load(self) -> dict:
        if self.path.exists():
            try:
                loaded = json.loads(self.path.read_text(encoding="utf-8"))
                if isinstance(loaded, dict):
                    merged = DEFAULT_SETTINGS.copy()
                    merged.update(loaded)
                    self.data = merged
            except (OSError, json.JSONDecodeError):
                self.data = DEFAULT_SETTINGS.copy()
        return self.data

    def save(self) -> None:
        try:
            self.path.write_text(json.dumps(self.data, indent=2), encoding="utf-8")
        except OSError:
            pass

    def set(self, key: str, value) -> None:
        self.data[key] = value
        self.save()
