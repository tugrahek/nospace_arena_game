from __future__ import annotations

import array
import math

import pygame


class AudioManager:
    def __init__(self, settings: dict):
        self.settings = settings
        self.available = False
        self.sounds: dict[str, pygame.mixer.Sound] = {}
        self.music_phase = 0.0
        self.music_timer = 0.0
        try:
            pygame.mixer.init(frequency=22050, size=-16, channels=1)
            self.available = True
        except pygame.error:
            self.available = False

        if self.available:
            self._build_sounds()
            self.set_volume(self.settings.get("volume", 0.45))

    def _tone(self, frequency: float, duration: float, volume: float = 0.35) -> pygame.mixer.Sound:
        sample_rate = 22050
        sample_count = max(1, int(sample_rate * duration))
        samples = array.array("h")
        envelope = max(1, int(sample_count * 0.15))
        for i in range(sample_count):
            t = i / sample_rate
            wave = math.sin(2.0 * math.pi * frequency * t)
            if i < envelope:
                gain = i / envelope
            elif i > sample_count - envelope:
                gain = (sample_count - i) / envelope
            else:
                gain = 1.0
            samples.append(int(32767 * volume * gain * wave))
        return pygame.mixer.Sound(buffer=samples.tobytes())

    def _build_sounds(self) -> None:
        self.sounds = {
            "move": self._tone(660, 0.04, 0.10),
            "menu": self._tone(540, 0.06, 0.14),
            "capture": self._tone(880, 0.18, 0.22),
            "hit": self._tone(180, 0.26, 0.28),
            "level": self._tone(1040, 0.32, 0.22),
            "powerup": self._tone(760, 0.20, 0.20),
            "shoot": self._tone(920, 0.08, 0.16),
            "stun": self._tone(320, 0.14, 0.18),
        }

    def set_volume(self, value: float) -> None:
        self.settings["volume"] = max(0.0, min(1.0, value))
        if not self.available:
            return
        for sound in self.sounds.values():
            sound.set_volume(self.settings["volume"])

    def play(self, name: str) -> None:
        if not self.available or not self.settings.get("sound_enabled", True):
            return
        sound = self.sounds.get(name)
        if sound is not None:
            sound.play()

    def update_music(self, dt: float) -> None:
        if not self.available or not self.settings.get("music_enabled", True):
            return
        self.music_timer += dt
        if self.music_timer < 1.2:
            return
        self.music_timer = 0.0
        freq = 230 + 40 * math.sin(self.music_phase)
        self.music_phase += 0.9
        tone = self._tone(freq, 0.28, 0.06)
        tone.set_volume(self.settings["volume"] * 0.7)
        tone.play()
