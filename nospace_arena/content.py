from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CharacterProfile:
    key: str
    name: str
    description: str
    primary: tuple[int, int, int]
    secondary: tuple[int, int, int]
    trail: tuple[int, int, int]
    cost: int
    unlocked_by_default: bool = False
    speed_multiplier: float = 1.0
    drawing_multiplier: float = 1.0
    extra_lives: int = 0
    shield_duration: float = 0.0
    capture_bonus: float = 1.0
    trail_bonus: float = 1.0
    combo_bonus: float = 0.0
    shot_cooldown_multiplier: float = 1.0
    style: str = "orb"


@dataclass(frozen=True)
class ThemeProfile:
    key: str
    name: str
    description: str
    background: tuple[int, int, int]
    free_area: tuple[int, int, int]
    solid_area: tuple[int, int, int]
    trail: tuple[int, int, int]
    border: tuple[int, int, int]
    hud_bg: tuple[int, int, int]
    text: tuple[int, int, int]
    accent: tuple[int, int, int]
    particle: tuple[int, int, int]
    overlay: tuple[int, int, int]
    trail_glow: tuple[int, int, int]
    danger: tuple[int, int, int]
    pattern: str
    cost: int
    unlocked_by_default: bool = False
    enemy_speed_scale: float = 1.0


@dataclass(frozen=True)
class PowerUpDefinition:
    key: str
    name: str
    description: str
    color: tuple[int, int, int]
    icon: str
    duration: float = 0.0
    award_text: str = ""


@dataclass(frozen=True)
class DifficultyProfile:
    key: str
    name: str
    description: str
    enemy_speed_multiplier: float = 1.0
    score_multiplier: float = 1.0
    powerup_rate_multiplier: float = 1.0
    combo_window_bonus: float = 0.0
    extra_lives: int = 0
    recovery_shield: float = 0.0


@dataclass(frozen=True)
class BoostProfile:
    key: str
    name: str
    description: str
    details: tuple[str, ...]
    color: tuple[int, int, int]
    cost: int
    start_shield: float = 0.0
    draw_speed_bonus: float = 0.0
    recovery_freeze: float = 0.0
    score_bonus: float = 0.0
    coin_bonus: float = 0.0
    early_enemy_slow: float = 0.0


CHARACTERS = {
    "spark": CharacterProfile(
        key="spark",
        name="Spark",
        description="Balanced starter pilot. Reliable speed, stable scoring, and a gentle combo edge.",
        primary=(248, 247, 255),
        secondary=(255, 170, 96),
        trail=(255, 214, 102),
        cost=0,
        unlocked_by_default=True,
        combo_bonus=0.1,
        style="orb",
    ),
    "glider": CharacterProfile(
        key="glider",
        name="Glider",
        description="Fast but fragile. Best for players who want sharp movement and quick closes.",
        primary=(155, 245, 255),
        secondary=(22, 184, 220),
        trail=(110, 242, 255),
        cost=140,
        speed_multiplier=1.18,
        drawing_multiplier=1.04,
        extra_lives=-1,
        trail_bonus=1.08,
        style="diamond",
    ),
    "bulwark": CharacterProfile(
        key="bulwark",
        name="Bulwark",
        description="Slow but safer. Extra life and opening shield give more room for mistakes.",
        primary=(255, 223, 126),
        secondary=(255, 124, 76),
        trail=(255, 195, 86),
        cost=180,
        speed_multiplier=0.92,
        drawing_multiplier=0.96,
        extra_lives=1,
        shield_duration=3.0,
        combo_bonus=0.05,
        style="shield",
    ),
    "surveyor": CharacterProfile(
        key="surveyor",
        name="Surveyor",
        description="Large-capture specialist. Risky long trails pay out with stronger territory rewards.",
        primary=(193, 255, 192),
        secondary=(67, 199, 125),
        trail=(127, 255, 190),
        cost=240,
        capture_bonus=1.18,
        trail_bonus=1.24,
        style="chevron",
    ),
    "volt": CharacterProfile(
        key="volt",
        name="Volt",
        description="High drawing speed. Fires faster while the Blaster is active.",
        primary=(185, 136, 255),
        secondary=(255, 104, 195),
        trail=(255, 125, 220),
        cost=320,
        drawing_multiplier=1.26,
        combo_bonus=0.12,
        shot_cooldown_multiplier=0.82,
        style="star",
    ),
}


THEMES = {
    "neon": ThemeProfile(
        key="neon",
        name="Neon Grid",
        description="Clean, readable arcade contrast. The default NoSpace: Arena look.",
        background=(6, 8, 18),
        free_area=(11, 14, 30),
        solid_area=(55, 214, 255),
        trail=(255, 95, 141),
        border=(126, 241, 255),
        hud_bg=(14, 18, 28),
        text=(233, 244, 255),
        accent=(255, 173, 92),
        particle=(82, 227, 255),
        overlay=(55, 214, 255),
        trail_glow=(255, 180, 205),
        danger=(255, 105, 105),
        pattern="scanlines",
        cost=0,
        unlocked_by_default=True,
        enemy_speed_scale=1.0,
    ),
    "jungle": ThemeProfile(
        key="jungle",
        name="Jungle",
        description="Dense green tones, warm highlights, and a living dot pattern.",
        background=(17, 34, 18),
        free_area=(28, 49, 24),
        solid_area=(120, 180, 72),
        trail=(247, 212, 93),
        border=(182, 231, 124),
        hud_bg=(24, 40, 24),
        text=(242, 246, 228),
        accent=(255, 150, 92),
        particle=(214, 255, 166),
        overlay=(124, 188, 88),
        trail_glow=(255, 242, 170),
        danger=(255, 130, 108),
        pattern="dots",
        cost=130,
    ),
    "ice": ThemeProfile(
        key="ice",
        name="Ice Rift",
        description="Bright crystal borders and a calmer high-visibility palette.",
        background=(184, 221, 245),
        free_area=(215, 239, 252),
        solid_area=(97, 171, 214),
        trail=(255, 137, 110),
        border=(255, 255, 255),
        hud_bg=(173, 212, 238),
        text=(18, 42, 62),
        accent=(255, 116, 84),
        particle=(255, 255, 255),
        overlay=(116, 198, 244),
        trail_glow=(255, 228, 216),
        danger=(255, 120, 120),
        pattern="crystals",
        cost=180,
        enemy_speed_scale=0.96,
    ),
    "space": ThemeProfile(
        key="space",
        name="Space",
        description="High-contrast cosmic arena with a starfield backdrop.",
        background=(4, 4, 12),
        free_area=(12, 13, 31),
        solid_area=(117, 94, 255),
        trail=(255, 111, 189),
        border=(210, 219, 255),
        hud_bg=(10, 10, 24),
        text=(238, 240, 255),
        accent=(118, 255, 208),
        particle=(255, 255, 255),
        overlay=(117, 94, 255),
        trail_glow=(255, 175, 222),
        danger=(255, 126, 126),
        pattern="stars",
        cost=250,
        enemy_speed_scale=1.02,
    ),
}


POWER_UPS = {
    "freeze": PowerUpDefinition(
        key="freeze",
        name="Freeze",
        description="Freezes enemies for a short time.",
        color=(165, 226, 255),
        icon="F",
        duration=4.5,
        award_text="Freeze engaged.",
    ),
    "slow": PowerUpDefinition(
        key="slow",
        name="Slow Motion",
        description="Temporarily reduces enemy speed.",
        color=(184, 255, 186),
        icon="S",
        duration=7.0,
        award_text="Enemies slowed.",
    ),
    "shield": PowerUpDefinition(
        key="shield",
        name="Shield",
        description="Absorbs one dangerous trail hit.",
        color=(255, 220, 110),
        icon="H",
        duration=6.0,
        award_text="Shield charged.",
    ),
    "speed_boost": PowerUpDefinition(
        key="speed_boost",
        name="Speed Boost",
        description="Briefly increases drawing speed.",
        color=(255, 145, 225),
        icon="V",
        duration=6.0,
        award_text="Drawing speed up.",
    ),
    "blaster": PowerUpDefinition(
        key="blaster",
        name="Blaster",
        description="Enables stun projectiles for a limited time.",
        color=(255, 112, 112),
        icon="B",
        duration=8.0,
        award_text="Blaster online.",
    ),
    "bomb": PowerUpDefinition(
        key="bomb",
        name="Bomb",
        description="Detonates on capture and temporarily disables nearby enemies.",
        color=(255, 188, 86),
        icon="X",
        duration=0.0,
        award_text="Bomb detonated.",
    ),
}


DIFFICULTIES = {
    "relaxed": DifficultyProfile(
        key="relaxed",
        name="Relaxed",
        description="A more forgiving tempo for learning routes and enemy tells.",
        enemy_speed_multiplier=0.88,
        score_multiplier=0.92,
        powerup_rate_multiplier=0.82,
        combo_window_bonus=1.3,
        extra_lives=1,
        recovery_shield=1.8,
    ),
    "arcade": DifficultyProfile(
        key="arcade",
        name="Arcade",
        description="Standard arcade balance with steady risk and reward.",
        enemy_speed_multiplier=1.0,
        score_multiplier=1.0,
        powerup_rate_multiplier=1.0,
        combo_window_bonus=0.0,
    ),
    "elite": DifficultyProfile(
        key="elite",
        name="Elite",
        description="Faster enemies, shorter reaction windows, and better scoring.",
        enemy_speed_multiplier=1.14,
        score_multiplier=1.22,
        powerup_rate_multiplier=1.08,
        combo_window_bonus=-0.7,
    ),
}


BOOSTS = {
    "guardian": BoostProfile(
        key="guardian",
        name="Guardian Core",
        description="Adds a light protective shield at the start of each level.",
        details=(
            "Adds protection at level start.",
            "Gives aggressive routes one early mistake buffer.",
            "Useful when entering newly unlocked stages.",
        ),
        color=(255, 219, 115),
        cost=120,
        start_shield=2.4,
    ),
    "rush": BoostProfile(
        key="rush",
        name="Rush Engine",
        description="Adds permanent drawing speed for smoother captures.",
        details=(
            "Speeds up movement while drawing a trail.",
            "Helps small and medium-risk captures finish sooner.",
            "A strong general pick for score chasing.",
        ),
        color=(255, 150, 225),
        cost=150,
        draw_speed_bonus=0.12,
    ),
    "stasis": BoostProfile(
        key="stasis",
        name="Stasis Trigger",
        description="Briefly freezes enemies after a life loss.",
        details=(
            "Creates a recovery window after a mistake.",
            "Reduces back-to-back life loss in hard stages.",
            "Still valuable with Assist Mode disabled.",
        ),
        color=(162, 224, 255),
        cost=180,
        recovery_freeze=1.7,
    ),
    "cutter": BoostProfile(
        key="cutter",
        name="Cutter Lens",
        description="Improves capture score and risk rewards.",
        details=(
            "Adds a bonus to territory capture scoring.",
            "Rewards players who can survive longer trails.",
            "One of the best economy picks for leaderboard runs.",
        ),
        color=(130, 255, 183),
        cost=220,
        score_bonus=0.16,
    ),
    "bounty": BoostProfile(
        key="bounty",
        name="Bounty Matrix",
        description="Increases coin rewards from cleared levels.",
        details=(
            "Pays more coins for each cleared level.",
            "Ideal for unlocking long-term content.",
            "Applies to run rewards, not daily mission payouts.",
        ),
        color=(255, 173, 92),
        cost=260,
        coin_bonus=0.3,
    ),
}
