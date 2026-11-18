# SPDX-License-Identifier: MIT
"""Controller for Arduino UNO Q Onboard RGB LEDs."""

import os
from typing import Tuple

LED_PATHS = {
    "r": "/sys/devices/platform/leds/leds/unoq:user-red1/brightness",
    "g": "/sys/devices/platform/leds/leds/unoq:user-green1/brightness",
    "b": "/sys/devices/platform/leds/leds/unoq:user-blue1/brightness",
}

COLOR_PRESETS = {
    "off": (0, 0, 0),
    "green": (0, 1, 0),     # 待命 / 開心
    "blue": (0, 0, 1),      # 聆聽 / 思考
    "red": (1, 0, 0),       # 專注 / 警示
    "pink": (1, 0, 1),      # 愛心 / 稱讚
    "yellow": (1, 1, 0),    # 提醒 / 喝水
    "cyan": (0, 1, 1),      # 輕快
    "white": (1, 1, 1),     # 全亮
}


class RgbLedController:
    """Safely manages UNO Q onboard RGB LED states."""

    def __init__(self):
        self.available = all(os.path.exists(p) for p in LED_PATHS.values())
        self.current_color = "off"
        if self.available:
            self.set_color("green")  # 開機綠燈待命

    def _write(self, color_channel: str, val: int) -> None:
        path = LED_PATHS.get(color_channel)
        if not path or not os.path.exists(path):
            return
        try:
            with open(path, "w") as f:
                f.write(str(val))
        except Exception:
            pass

    def set_rgb(self, r: int, g: int, b: int) -> None:
        """Set raw binary RGB values (0 or 1)."""
        self._write("r", 1 if r else 0)
        self._write("g", 1 if g else 0)
        self._write("b", 1 if b else 0)

    def set_color(self, name: str) -> None:
        """Set predefined color ('green', 'blue', 'pink', 'red', etc.)."""
        preset = COLOR_PRESETS.get(name.lower(), COLOR_PRESETS["off"])
        self.current_color = name.lower()
        self.set_rgb(*preset)

    def close(self) -> None:
        self.set_color("off")
