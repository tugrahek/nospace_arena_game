from __future__ import annotations

import math
import random

import pygame

from .config import GAME_TITLE, GRID_HEIGHT, HUD_HEIGHT, SCREEN_HEIGHT, SCREEN_WIDTH, TARGET_FREE_RATIO, TILE_SIZE
from .content import BOOSTS, CHARACTERS, DIFFICULTIES, THEMES


class FontSet:
    def __init__(self):
        self.title = pygame.font.SysFont("consolas", 34, bold=True)
        self.heading = pygame.font.SysFont("consolas", 24, bold=True)
        self.body = pygame.font.SysFont("consolas", 18)
        self.small = pygame.font.SysFont("consolas", 15)
        self.tiny = pygame.font.SysFont("consolas", 13)


class Menu:
    def __init__(self, title: str, items: list[str]):
        self.title = title
        self.items = items
        self.index = 0

    def move(self, delta: int) -> None:
        self.index = (self.index + delta) % len(self.items)

    def selected(self) -> str:
        return self.items[self.index]


def blend(color_a, color_b, ratio: float):
    ratio = max(0.0, min(1.0, ratio))
    return tuple(int(color_a[index] * (1.0 - ratio) + color_b[index] * ratio) for index in range(3))


def wrap_text(font: pygame.font.Font, text: str, max_width: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        proposal = word if not current else f"{current} {word}"
        if font.size(proposal)[0] <= max_width:
            current = proposal
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines or [""]


def draw_wrapped_text(surface: pygame.Surface, font: pygame.font.Font, text: str, color, rect: pygame.Rect, line_height: int | None = None) -> int:
    line_height = line_height or font.get_linesize()
    y = rect.y
    for line in wrap_text(font, text, rect.width):
        surface.blit(font.render(line, True, color), (rect.x, y))
        y += line_height
    return y


def glow_text(surface: pygame.Surface, font: pygame.font.Font, text: str, color, pos: tuple[int, int], glow_color=None) -> pygame.Rect:
    glow_color = glow_color or color
    glow = font.render(text, True, glow_color)
    glow.set_alpha(80)
    for ox, oy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
        surface.blit(glow, (pos[0] + ox, pos[1] + oy))
    text_surf = font.render(text, True, color)
    return surface.blit(text_surf, pos)


def draw_themed_background(surface: pygame.Surface, theme, tick: float) -> None:
    surface.fill(theme.background)
    vignette = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    vignette.fill((0, 0, 0, 0))
    pygame.draw.rect(vignette, (0, 0, 0, 72), vignette.get_rect(), 24)
    surface.blit(vignette, (0, 0))
    if theme.pattern == "stars":
        star_rng = random.Random(11)
        for _ in range(85):
            x = star_rng.randint(0, SCREEN_WIDTH - 1)
            y = star_rng.randint(0, SCREEN_HEIGHT - 1)
            size = 1 if star_rng.random() < 0.82 else 2
            color = tuple(min(255, c + star_rng.randint(0, 35)) for c in theme.particle)
            surface.fill(color, pygame.Rect(x, y, size, size))
    elif theme.pattern == "scanlines":
        for y in range(0, SCREEN_HEIGHT, 6):
            line_color = tuple(max(0, channel - 8) for channel in theme.background)
            pygame.draw.line(surface, line_color, (0, y), (SCREEN_WIDTH, y), 1)
        for x in range(0, SCREEN_WIDTH, 40):
            brightness = 0.08 + (math.sin(tick * 1.6 + x * 0.025) + 1.0) * 0.05
            color = tuple(min(255, int(theme.border[index] * brightness + theme.background[index] * (1.0 - brightness))) for index in range(3))
            pygame.draw.line(surface, color, (x, 0), (x, SCREEN_HEIGHT), 1)
        for y in range(0, SCREEN_HEIGHT, 40):
            brightness = 0.06 + (math.sin(tick * 1.25 + y * 0.018) + 1.0) * 0.04
            color = tuple(min(255, int(theme.overlay[index] * brightness + theme.background[index] * (1.0 - brightness))) for index in range(3))
            pygame.draw.line(surface, color, (0, y), (SCREEN_WIDTH, y), 1)
        scan_y = int((tick * 90) % SCREEN_HEIGHT)
        overlay = pygame.Surface((SCREEN_WIDTH, 14), pygame.SRCALPHA)
        overlay.fill((*theme.accent, 22))
        surface.blit(overlay, (0, scan_y))
    elif theme.pattern == "dots":
        for y in range(14, SCREEN_HEIGHT, 24):
            for x in range(14, SCREEN_WIDTH, 24):
                radius = 1 + int((math.sin(tick + x * 0.015 + y * 0.01) + 1.0) * 0.6)
                pygame.draw.circle(surface, theme.particle, (x, y), radius)
    elif theme.pattern == "crystals":
        for x in range(0, SCREEN_WIDTH + 60, 72):
            offset = int(math.sin(tick * 1.6 + x * 0.02) * 8)
            points = [(x + 10, 0), (x + 34, 42 + offset), (x + 58, 0)]
            pygame.draw.polygon(surface, tuple(min(255, c + 8) for c in theme.particle), points, 1)
    else:
        for y in range(0, SCREEN_HEIGHT, 56):
            alpha = 40 + int((math.sin(tick * 1.2 + y * 0.03) + 1.0) * 20)
            overlay = pygame.Surface((SCREEN_WIDTH, 2), pygame.SRCALPHA)
            overlay.fill((*theme.accent, alpha))
            surface.blit(overlay, (0, y))


def _draw_panel(surface: pygame.Surface, rect: pygame.Rect, theme) -> None:
    shadow = rect.move(8, 8)
    pygame.draw.rect(surface, (0, 0, 0), shadow, border_radius=8)
    pygame.draw.rect(surface, theme.hud_bg, rect, border_radius=8)
    pygame.draw.rect(surface, theme.border, rect, 2, border_radius=8)


def draw_notice(surface: pygame.Surface, fonts: FontSet, theme, text: str) -> None:
    if not text:
        return
    rect = pygame.Rect(130, SCREEN_HEIGHT - 40, SCREEN_WIDTH - 260, 24)
    draw_wrapped_text(surface, fonts.tiny, text, theme.accent, rect, 14)


def draw_menu(surface: pygame.Surface, fonts: FontSet, menu: Menu, theme, footer: str) -> None:
    title = fonts.title.render(GAME_TITLE, True, theme.text)
    title_rect = title.get_rect(center=(SCREEN_WIDTH // 2, 62))
    glow = fonts.title.render(GAME_TITLE, True, theme.border)
    glow.set_alpha(90)
    surface.blit(glow, glow.get_rect(center=(SCREEN_WIDTH // 2, 62)))
    surface.blit(title, title_rect)

    panel = pygame.Rect(118, 126, SCREEN_WIDTH - 236, 434)
    _draw_panel(surface, panel, theme)

    heading = fonts.heading.render(menu.title, True, theme.text)
    surface.blit(heading, (panel.x + 30, panel.y + 20))

    footer_height = 56
    item_top = panel.y + 60
    available_height = panel.height - 60 - footer_height - 16
    item_step = max(24, min(32, available_height // max(1, len(menu.items))))
    for index, item in enumerate(menu.items):
        selected = index == menu.index
        item_rect = pygame.Rect(panel.x + 24, item_top + index * item_step, panel.width - 48, max(22, item_step - 4))
        if selected:
            pygame.draw.rect(surface, theme.accent, item_rect, border_radius=6)
        color = theme.background if selected else theme.text
        surface.blit(fonts.small.render(item, True, color), (item_rect.x + 14, item_rect.y + max(3, (item_rect.height - fonts.small.get_height()) // 2)))

    footer_rect = pygame.Rect(panel.x + 24, panel.bottom - footer_height - 6, panel.width - 48, footer_height)
    draw_wrapped_text(surface, fonts.tiny, footer, theme.text, footer_rect, 14)


def draw_selection_panel(surface: pygame.Surface, fonts: FontSet, title: str, options: list, selected_index: int, theme, hint: str) -> None:
    panel = pygame.Rect(54, 118, SCREEN_WIDTH - 108, 414)
    _draw_panel(surface, panel, theme)

    header = fonts.heading.render(title, True, theme.text)
    surface.blit(header, (panel.x + 24, panel.y + 18))

    list_rect = pygame.Rect(panel.x + 20, panel.y + 58, 260, panel.height - 82)
    detail_rect = pygame.Rect(panel.x + 298, panel.y + 58, panel.width - 318, panel.height - 82)
    pygame.draw.rect(surface, theme.background, list_rect, border_radius=14)
    pygame.draw.rect(surface, theme.background, detail_rect, border_radius=14)
    pygame.draw.rect(surface, theme.border, list_rect, 1, border_radius=14)
    pygame.draw.rect(surface, theme.border, detail_rect, 1, border_radius=14)

    item_height = 54
    for index, option in enumerate(options):
        item_rect = pygame.Rect(list_rect.x + 10, list_rect.y + 10 + index * item_height, list_rect.width - 20, 42)
        selected = index == selected_index
        if selected:
            pygame.draw.rect(surface, theme.accent, item_rect, border_radius=12)
        swatch = option.primary if hasattr(option, "primary") else option.solid_area
        text_color = theme.background if selected else theme.text
        pygame.draw.circle(surface, swatch, (item_rect.x + 16, item_rect.centery), 10)
        surface.blit(fonts.small.render(option.name, True, text_color), (item_rect.x + 36, item_rect.y + 11))

    selected = options[selected_index]
    swatch = selected.primary if hasattr(selected, "primary") else selected.solid_area
    pygame.draw.circle(surface, swatch, (detail_rect.x + 28, detail_rect.y + 25), 14)
    surface.blit(fonts.body.render(selected.name, True, theme.text), (detail_rect.x + 52, detail_rect.y + 14))
    draw_wrapped_text(surface, fonts.small, selected.description, theme.text, pygame.Rect(detail_rect.x + 18, detail_rect.y + 52, detail_rect.width - 36, 84), 18)

    stats_y = detail_rect.y + 142
    if hasattr(selected, "speed_multiplier"):
        stats = [
            f"Move speed x{selected.speed_multiplier:.2f}",
            f"Draw speed x{selected.drawing_multiplier:.2f}",
            f"Life delta {selected.extra_lives:+d}",
            f"Capture bonus x{selected.capture_bonus:.2f}",
            f"Risk bonus x{selected.trail_bonus:.2f}",
        ]
    else:
        stats = [
            f"Pattern {selected.pattern}",
            f"Enemy speed x{selected.enemy_speed_scale:.2f}",
            f"Trail glow {selected.trail_glow}",
            f"Danger tint {selected.danger}",
        ]
    for line in stats:
        surface.blit(fonts.small.render(line, True, theme.text), (detail_rect.x + 18, stats_y))
        stats_y += 24

    hint_rect = pygame.Rect(detail_rect.x + 18, detail_rect.bottom - 54, detail_rect.width - 36, 40)
    draw_wrapped_text(surface, fonts.tiny, hint, theme.accent, hint_rect, 15)


def draw_settings_panel(surface: pygame.Surface, fonts: FontSet, menu: Menu, settings_lines: list[str], theme) -> None:
    panel = pygame.Rect(130, 134, SCREEN_WIDTH - 260, 370)
    _draw_panel(surface, panel, theme)
    surface.blit(fonts.heading.render(menu.title, True, theme.text), (panel.x + 24, panel.y + 18))

    for index, line in enumerate(settings_lines):
        selected = index == menu.index
        item_rect = pygame.Rect(panel.x + 22, panel.y + 66 + index * 40, panel.width - 44, 32)
        if selected:
            pygame.draw.rect(surface, theme.accent, item_rect, border_radius=10)
        color = theme.background if selected else theme.text
        surface.blit(fonts.small.render(line, True, color), (item_rect.x + 14, item_rect.y + 8))

    hint_rect = pygame.Rect(panel.x + 24, panel.bottom - 52, panel.width - 48, 34)
    draw_wrapped_text(surface, fonts.tiny, "Left and Right adjust values. Enter confirms. Escape returns without resetting the previous menu cursor.", theme.accent, hint_rect, 15)


def draw_how_to_play(surface: pygame.Surface, fonts: FontSet, theme) -> None:
    panel = pygame.Rect(72, 118, SCREEN_WIDTH - 144, 416)
    _draw_panel(surface, panel, theme)

    title = fonts.heading.render("How to Play", True, theme.text)
    surface.blit(title, (panel.x + 24, panel.y + 18))

    lines = [
        "Move with Arrow keys or WASD while staying on the solid border when you are safe.",
        "Step into open space to start drawing a trail, then reconnect it to the border to capture territory.",
        "If an enemy touches your active trail before you close it, you lose the draw and take a hit.",
        "Power-ups appear only in open territory and activate only when you capture the area containing them.",
        "Blaster lets you fire with Space, Left Ctrl, or Right Ctrl and temporarily stuns enemies.",
        "Big captures, longer risky trails, and quick consecutive closes build score and combo.",
        "P pauses, R restarts after game over, Escape returns, M/N toggle audio, [ and ] change volume.",
    ]

    y = panel.y + 56
    for line in lines:
        y = draw_wrapped_text(surface, fonts.small, line, theme.text, pygame.Rect(panel.x + 24, y, panel.width - 48, 42), 18) + 10


def draw_hud(surface: pygame.Surface, fonts: FontSet, theme, session, coins: int) -> None:
    hud_rect = pygame.Rect(0, GRID_HEIGHT * TILE_SIZE, SCREEN_WIDTH, HUD_HEIGHT)
    pygame.draw.rect(surface, theme.hud_bg, hud_rect)
    pygame.draw.line(surface, theme.border, (0, hud_rect.y), (SCREEN_WIDTH, hud_rect.y), 2)
    pygame.draw.rect(surface, tuple(max(0, channel - 12) for channel in theme.background), hud_rect.inflate(-12, -14), 1, border_radius=8)

    char_name = CHARACTERS[session.character_key].name
    theme_name = THEMES[session.theme_key].name
    difficulty_name = DIFFICULTIES[session.difficulty_key].name
    boost_name = BOOSTS[session.equipped_boost_key].name if session.equipped_boost_key in BOOSTS else "No Boost"

    line1 = f"SCORE {session.score}   LIVES {session.lives}   LEVEL {session.level}   COINS {coins}"
    line2 = f"CAPTURE {session.capture_percent():5.1f}%   TARGET {(1.0 - TARGET_FREE_RATIO) * 100:5.1f}%   LAST +{session.last_capture_points}"
    line3 = f"{char_name} | {theme_name} | {difficulty_name} | {boost_name}"
    line4 = session.active_effect_label()

    glow_text(surface, fonts.body, line1, theme.text, (16, hud_rect.y + 10), theme.border)
    glow_text(surface, fonts.small, line2, theme.text, (16, hud_rect.y + 36), theme.overlay)
    draw_wrapped_text(surface, fonts.tiny, line3, theme.accent, pygame.Rect(16, hud_rect.y + 58, SCREEN_WIDTH - 32, 16), 14)
    draw_wrapped_text(surface, fonts.tiny, line4, theme.text, pygame.Rect(16, hud_rect.y + 72, SCREEN_WIDTH - 32, 16), 14)

    combo_bar = pygame.Rect(16, hud_rect.y + 94, 220, 10)
    pygame.draw.rect(surface, tuple(max(0, channel - 10) for channel in theme.background), combo_bar.inflate(2, 2), border_radius=6)
    pygame.draw.rect(surface, theme.background, combo_bar, border_radius=5)
    combo_fill = combo_bar.copy()
    combo_fill.width = int(combo_bar.width * min(1.0, session.combo_timer / session.combo_window()))
    pygame.draw.rect(surface, theme.accent, combo_fill, border_radius=5)
    combo_label = f"Combo x{session.combo_multiplier():.2f}  Chain {session.combo_chain}"
    glow_text(surface, fonts.tiny, combo_label, theme.text, (16, hud_rect.y + 108), theme.accent)

    danger_bar = pygame.Rect(264, hud_rect.y + 94, 220, 10)
    pygame.draw.rect(surface, tuple(max(0, channel - 10) for channel in theme.background), danger_bar.inflate(2, 2), border_radius=6)
    pygame.draw.rect(surface, theme.background, danger_bar, border_radius=5)
    danger_fill = danger_bar.copy()
    danger_fill.width = int(danger_bar.width * session.danger_level)
    pygame.draw.rect(surface, theme.danger, danger_fill, border_radius=5)
    glow_text(surface, fonts.tiny, "Danger", theme.text, (264, hud_rect.y + 108), theme.danger)

    shot_status = "READY" if session.player.can_shoot() and session.shot_cooldown <= 0 else "CHARGING" if session.player.can_shoot() else "OFF"
    shot_color = theme.accent if shot_status == "READY" else theme.text if shot_status == "CHARGING" else blend(theme.text, theme.background, 0.35)
    glow_text(surface, fonts.small, f"Shots {shot_status}", shot_color, (SCREEN_WIDTH - 180, hud_rect.y + 92), theme.border)

    if session.toast:
        toast_rect = pygame.Rect(500, hud_rect.y + 108, SCREEN_WIDTH - 516, 24)
        draw_wrapped_text(surface, fonts.tiny, session.toast, theme.text, toast_rect, 14)


def draw_danger_overlay(surface: pygame.Surface, theme, danger_level: float) -> None:
    if danger_level <= 0:
        return
    overlay = pygame.Surface((SCREEN_WIDTH, GRID_HEIGHT * TILE_SIZE), pygame.SRCALPHA)
    alpha = int(52 * danger_level)
    overlay.fill((*theme.danger, alpha // 3))
    pygame.draw.rect(overlay, (*theme.danger, alpha + 20), overlay.get_rect(), 6)
    surface.blit(overlay, (0, 0))


def draw_center_message(surface: pygame.Surface, fonts: FontSet, theme, title: str, lines: list[str]) -> None:
    box = pygame.Rect(132, 152, SCREEN_WIDTH - 264, 206)
    _draw_panel(surface, box, theme)

    title_surf = fonts.title.render(title, True, theme.text)
    surface.blit(title_surf, title_surf.get_rect(center=(box.centerx, box.y + 40)))
    y = box.y + 86
    for line in lines:
        y = draw_wrapped_text(surface, fonts.body, line, theme.text, pygame.Rect(box.x + 24, y, box.width - 48, 36), 22) + 6


def draw_pause_overlay(surface: pygame.Surface, fonts: FontSet, theme, session) -> None:
    box = pygame.Rect(162, 164, SCREEN_WIDTH - 324, 182)
    _draw_panel(surface, box, theme)
    title = fonts.title.render("Paused", True, theme.text)
    surface.blit(title, title.get_rect(center=(box.centerx, box.y + 38)))
    lines = [
        f"Score {session.score} | Level {session.level} | Best Combo x{session.best_combo:.2f}",
        "Press P or Enter to resume. R restarts the run. Escape returns to the main menu.",
    ]
    y = box.y + 84
    for line in lines:
        y = draw_wrapped_text(surface, fonts.small, line, theme.text, pygame.Rect(box.x + 22, y, box.width - 44, 36), 18) + 8


def draw_level_select(surface: pygame.Surface, fonts: FontSet, theme, selected_level: int, best_level: int, level_scores: dict[str, int]) -> None:
    panel = pygame.Rect(110, 120, SCREEN_WIDTH - 220, 412)
    _draw_panel(surface, panel, theme)
    surface.blit(fonts.heading.render("Level Select", True, theme.text), (panel.x + 24, panel.y + 18))

    list_rect = pygame.Rect(panel.x + 22, panel.y + 58, 250, panel.height - 82)
    detail_rect = pygame.Rect(panel.x + 292, panel.y + 58, panel.width - 314, panel.height - 82)
    pygame.draw.rect(surface, theme.background, list_rect, border_radius=14)
    pygame.draw.rect(surface, theme.background, detail_rect, border_radius=14)
    pygame.draw.rect(surface, theme.border, list_rect, 1, border_radius=14)
    pygame.draw.rect(surface, theme.border, detail_rect, 1, border_radius=14)

    for level in range(1, 11):
        unlocked = level <= max(1, best_level)
        item_rect = pygame.Rect(list_rect.x + 10, list_rect.y + 10 + (level - 1) * 34, list_rect.width - 20, 28)
        selected = level == selected_level
        if selected:
            pygame.draw.rect(surface, theme.accent, item_rect, border_radius=10)
        color = theme.background if selected else theme.text
        label = f"Level {level}"
        if not unlocked:
            label += "  LOCKED"
        surface.blit(fonts.small.render(label, True, color), (item_rect.x + 12, item_rect.y + 6))

    unlocked = selected_level <= max(1, best_level)
    best_score = level_scores.get(str(selected_level), 0)
    detail_lines = [
        f"Best Score: {best_score}",
        f"Status: {'Unlocked' if unlocked else 'Locked'}",
        f"Clear Level {max(1, selected_level - 1)} to unlock." if not unlocked else "Start from this level and chase a better record.",
        "Enter starts the selected unlocked level.",
    ]
    y = detail_rect.y + 16
    for line in detail_lines:
        y = draw_wrapped_text(surface, fonts.small, line, theme.text, pygame.Rect(detail_rect.x + 18, y, detail_rect.width - 36, 40), 18) + 8


def draw_daily_missions(surface: pygame.Surface, fonts: FontSet, theme, missions: list[dict], selected_index: int, coins: int, mission_date: str) -> None:
    panel = pygame.Rect(74, 116, SCREEN_WIDTH - 148, 420)
    _draw_panel(surface, panel, theme)
    surface.blit(fonts.heading.render("Daily Missions", True, theme.text), (panel.x + 24, panel.y + 18))
    surface.blit(fonts.small.render(f"Coins {coins}", True, theme.accent), (panel.right - 140, panel.y + 20))

    for index, mission in enumerate(missions):
        item_rect = pygame.Rect(panel.x + 22, panel.y + 60 + index * 104, panel.width - 44, 90)
        selected = index == selected_index
        border_color = theme.accent if selected else theme.border
        pygame.draw.rect(surface, theme.background, item_rect, border_radius=14)
        pygame.draw.rect(surface, border_color, item_rect, 2, border_radius=14)
        title = mission["title"]
        status = "Claim" if mission["completed"] and not mission["claimed"] else "Claimed" if mission["claimed"] else "In Progress"
        progress_text = f"{int(mission['progress'])}/{int(mission['target'])}"
        surface.blit(fonts.small.render(title, True, theme.text), (item_rect.x + 14, item_rect.y + 10))
        surface.blit(fonts.tiny.render(status, True, theme.accent), (item_rect.right - 94, item_rect.y + 12))
        draw_wrapped_text(surface, fonts.tiny, mission["description"], theme.text, pygame.Rect(item_rect.x + 14, item_rect.y + 34, item_rect.width - 150, 28), 14)
        surface.blit(fonts.tiny.render(f"Reward {mission['reward']} coin", True, theme.text), (item_rect.x + 14, item_rect.bottom - 22))
        surface.blit(fonts.tiny.render(progress_text, True, theme.text), (item_rect.right - 90, item_rect.bottom - 22))
        bar_rect = pygame.Rect(item_rect.x + 14, item_rect.bottom - 42, item_rect.width - 28, 8)
        pygame.draw.rect(surface, theme.hud_bg, bar_rect, border_radius=4)
        fill = bar_rect.copy()
        fill.width = int(bar_rect.width * min(1.0, mission["progress"] / max(1, mission["target"])))
        pygame.draw.rect(surface, theme.accent, fill, border_radius=4)

    draw_wrapped_text(surface, fonts.tiny, f"Refresh date {mission_date}. Enter claims a completed mission.", theme.accent, pygame.Rect(panel.x + 22, panel.bottom - 24, panel.width - 44, 18), 14)


def draw_store_panel(surface: pygame.Surface, fonts: FontSet, theme, category_name: str, items: list[dict], selected_index: int, coins: int, equipped_boost: str) -> None:
    panel = pygame.Rect(56, 112, SCREEN_WIDTH - 112, 428)
    _draw_panel(surface, panel, theme)
    surface.blit(fonts.heading.render(f"Store - {category_name}", True, theme.text), (panel.x + 24, panel.y + 18))
    surface.blit(fonts.small.render(f"Coins {coins}", True, theme.accent), (panel.right - 132, panel.y + 20))

    list_rect = pygame.Rect(panel.x + 20, panel.y + 58, 290, panel.height - 82)
    detail_rect = pygame.Rect(panel.x + 330, panel.y + 58, panel.width - 350, panel.height - 82)
    pygame.draw.rect(surface, theme.background, list_rect, border_radius=14)
    pygame.draw.rect(surface, theme.background, detail_rect, border_radius=14)
    pygame.draw.rect(surface, theme.border, list_rect, 1, border_radius=14)
    pygame.draw.rect(surface, theme.border, detail_rect, 1, border_radius=14)

    for index, item in enumerate(items):
        item_rect = pygame.Rect(list_rect.x + 10, list_rect.y + 10 + index * 48, list_rect.width - 20, 38)
        selected = index == selected_index
        if selected:
            pygame.draw.rect(surface, theme.accent, item_rect, border_radius=10)
        text_color = theme.background if selected else theme.text
        status = "Owned" if item["owned"] else f"{item['cost']} coin"
        if item["category"] == "Boosts" and item["key"] == equipped_boost:
            status = "Equipped"
        surface.blit(fonts.small.render(item["name"], True, text_color), (item_rect.x + 12, item_rect.y + 10))
        surface.blit(fonts.tiny.render(status, True, text_color), (item_rect.right - 84, item_rect.y + 12))

    item = items[selected_index]
    y = detail_rect.y + 18
    surface.blit(fonts.body.render(item["name"], True, theme.text), (detail_rect.x + 18, y))
    y += 34
    y = draw_wrapped_text(surface, fonts.small, item["description"], theme.text, pygame.Rect(detail_rect.x + 18, y, detail_rect.width - 36, 70), 18) + 10
    for line in item["details"]:
        y = draw_wrapped_text(surface, fonts.tiny, line, theme.text, pygame.Rect(detail_rect.x + 18, y, detail_rect.width - 36, 28), 14) + 6

    action = "Enter to equip" if item["owned"] and item["category"] == "Boosts" else "Enter to select" if item["owned"] else "Enter to unlock"
    hint_rect = pygame.Rect(detail_rect.x + 18, detail_rect.bottom - 46, detail_rect.width - 36, 34)
    draw_wrapped_text(surface, fonts.tiny, action + ". Left and Right change store category.", theme.accent, hint_rect, 14)


def draw_boost_info(surface: pygame.Surface, fonts: FontSet, theme, boost_keys: list[str], selected_index: int, unlocked_boosts: set[str], equipped_boost: str) -> None:
    panel = pygame.Rect(68, 114, SCREEN_WIDTH - 136, 422)
    _draw_panel(surface, panel, theme)
    surface.blit(fonts.heading.render("Boost Info", True, theme.text), (panel.x + 24, panel.y + 18))

    list_rect = pygame.Rect(panel.x + 20, panel.y + 58, 270, panel.height - 82)
    detail_rect = pygame.Rect(panel.x + 308, panel.y + 58, panel.width - 328, panel.height - 82)
    pygame.draw.rect(surface, theme.background, list_rect, border_radius=14)
    pygame.draw.rect(surface, theme.background, detail_rect, border_radius=14)
    pygame.draw.rect(surface, theme.border, list_rect, 1, border_radius=14)
    pygame.draw.rect(surface, theme.border, detail_rect, 1, border_radius=14)

    for index, key in enumerate(boost_keys):
        boost = BOOSTS[key]
        item_rect = pygame.Rect(list_rect.x + 10, list_rect.y + 10 + index * 48, list_rect.width - 20, 38)
        selected = index == selected_index
        if selected:
            pygame.draw.rect(surface, theme.accent, item_rect, border_radius=10)
        text_color = theme.background if selected else theme.text
        status = "Equipped" if key == equipped_boost else "Unlocked" if key in unlocked_boosts else f"{boost.cost} coin"
        surface.blit(fonts.small.render(boost.name, True, text_color), (item_rect.x + 12, item_rect.y + 10))
        surface.blit(fonts.tiny.render(status, True, text_color), (item_rect.right - 86, item_rect.y + 12))

    boost = BOOSTS[boost_keys[selected_index]]
    y = detail_rect.y + 18
    surface.blit(fonts.body.render(boost.name, True, theme.text), (detail_rect.x + 18, y))
    y += 34
    y = draw_wrapped_text(surface, fonts.small, boost.description, theme.text, pygame.Rect(detail_rect.x + 18, y, detail_rect.width - 36, 60), 18) + 10
    for line in boost.details:
        y = draw_wrapped_text(surface, fonts.tiny, line, theme.text, pygame.Rect(detail_rect.x + 18, y, detail_rect.width - 36, 30), 14) + 6
    surface.blit(fonts.tiny.render(f"Cost {boost.cost} coin", True, theme.accent), (detail_rect.x + 18, detail_rect.bottom - 28))
