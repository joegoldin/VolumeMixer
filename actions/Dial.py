from src.backend.DeckManagement.InputIdentifier import Input
from src.backend.PluginManager.ActionBase import ActionBase
from src.backend.DeckManagement.DeckController import DeckController
from src.backend.PageManagement.Page import Page
from src.backend.PluginManager.PluginBase import PluginBase

import globals as gl
from loguru import logger as log
import math
import os
import threading

from PIL import Image, ImageDraw


class Dial(ActionBase):
    # How long (in ticks) the +/- icon overlay persists after a scroll
    SCROLL_ICON_TICKS = 4

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.plugin_base.volume_actions.append(self)

        self._scroll_direction = None  # "up", "down", or None
        self._scroll_ticks_remaining = 0
        self._lock = threading.Lock()

        self._icon_normal = None
        self._icon_plus = None
        self._icon_minus = None
        self._icon_muted = None
        self._load_icons()

    def _load_icons(self):
        asset_dir = os.path.join(self.plugin_base.PATH, "assets")
        up_path = os.path.join(asset_dir, "volume_up.png")
        down_path = os.path.join(asset_dir, "volume_down.png")

        with Image.open(up_path) as img:
            self._icon_normal = img.copy().convert("RGBA")
        with Image.open(up_path) as img:
            self._icon_plus = img.copy().convert("RGBA")
            self._draw_overlay(self._icon_plus, "+")
        with Image.open(down_path) as img:
            self._icon_minus = img.copy().convert("RGBA")
            self._draw_overlay(self._icon_minus, "-")
        with Image.open(down_path) as img:
            base = img.copy().convert("RGBA")
            # Tint red for muted
            r, g, b, a = base.split()
            muted_img = Image.merge("RGBA", (r, Image.new("L", base.size, 0), Image.new("L", base.size, 0), a))
            self._icon_muted = muted_img

    def _draw_overlay(self, icon: Image.Image, symbol: str):
        """Draw a +/- symbol in the bottom-right corner of the icon."""
        draw = ImageDraw.Draw(icon)
        size = icon.width
        symbol_size = size // 3
        cx = size - symbol_size // 2 - 4
        cy = size - symbol_size // 2 - 4
        half = symbol_size // 2 - 2
        line_w = max(2, size // 24)

        # Horizontal bar (for both + and -)
        draw.line([(cx - half, cy), (cx + half, cy)], fill=(255, 255, 255, 255), width=line_w)
        # Vertical bar (only for +)
        if symbol == "+":
            draw.line([(cx, cy - half), (cx, cy + half)], fill=(255, 255, 255, 255), width=line_w)
        del draw

    def on_ready(self):
        self.current_state = -1
        self.on_tick()
        self.current_state = -1

    def on_tick(self):
        index = self.get_index()

        inputs = self.plugin_base.pulse.sink_input_list()
        if index < len(inputs):
            with self._lock:
                if self._scroll_ticks_remaining > 0:
                    self._scroll_ticks_remaining -= 1
                    if self._scroll_ticks_remaining == 0:
                        self._scroll_direction = None
            self.update_display()
        else:
            self.clear()

    def clear(self):
        self.set_media(image=None, update=False)
        self.set_top_label(None, update=False)
        self.set_bottom_label(None, update=False)
        self.set_center_label(None)

    def event_callback(self, event, data):
        inputs = self.plugin_base.pulse.sink_input_list()

        index = self.get_index()
        if index >= len(inputs):
            return

        name = inputs[index].name
        volume = inputs[index].volume.value_flat
        muted = inputs[index].mute != 0

        if event == Input.Dial.Events.SHORT_UP:
            muted = not muted
            self.plugin_base.pulse.mute(obj=inputs[index], mute=muted)

        elif event == Input.Dial.Events.TURN_CW:
            volume = min(1, volume + self.plugin_base.volume_increment)
            self.plugin_base.pulse.volume_set_all_chans(obj=inputs[index], vol=volume)
            with self._lock:
                self._scroll_direction = "up"
                self._scroll_ticks_remaining = self.SCROLL_ICON_TICKS

        elif event == Input.Dial.Events.TURN_CCW:
            volume = max(0, volume - self.plugin_base.volume_increment)
            self.plugin_base.pulse.volume_set_all_chans(obj=inputs[index], vol=volume)
            with self._lock:
                self._scroll_direction = "down"
                self._scroll_ticks_remaining = self.SCROLL_ICON_TICKS

        self.update_display(volume=volume, muted=muted, name=name)

    def get_index(self) -> int:
        start_index = self.plugin_base.start_index
        own_index = int(self.input_ident.json_identifier)
        index = start_index + own_index
        return index

    def update_display(self, volume=None, muted=None, name=None):
        if volume is None or muted is None or name is None:
            inputs = self.plugin_base.pulse.sink_input_list()
            index = self.get_index()
            if volume is None:
                volume = inputs[index].volume.value_flat
            if muted is None:
                muted = inputs[index].mute != 0
            if name is None:
                name = inputs[index].name

        # Build the dial image with icon + volume bar
        dial_image = self._render_dial_image(volume, muted)
        self.set_media(image=dial_image, update=False)

        # Volume % at top, app name at bottom (above the bar)
        if not muted:
            volume_label = str(math.ceil(volume * 100)) + "%"
            label_color = [255, 255, 255]
        else:
            volume_label = "- " + self.plugin_base.lm.get("input.muted").upper() + " -"
            label_color = [255, 0, 0]

        self.set_top_label(text=volume_label, color=label_color, font_size=16, update=False)
        self.set_center_label(text=None, update=False)
        self.set_bottom_label(text=name, font_size=12)

    def _render_dial_image(self, volume: float, muted: bool) -> Image.Image:
        """Render the dial touchscreen image with icon and volume bar."""
        # Dial area is 200x100
        width, height = 200, 100
        img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # --- Volume bar ---
        # Sits between the icon area and the bottom label
        bar_height = 5
        bar_y_start = height - 20  # leave ~20px for bottom label
        bar_margin = 10

        # Bar background (dark grey track)
        draw.rounded_rectangle(
            [(bar_margin, bar_y_start), (width - bar_margin, bar_y_start + bar_height)],
            radius=2,
            fill=(60, 60, 60, 255)
        )

        # Bar fill
        bar_inner_width = width - 2 * bar_margin
        fill_width = int(bar_inner_width * min(1.0, max(0.0, volume)))
        if fill_width > 0:
            if muted:
                bar_color = (180, 40, 40, 255)
            else:
                # Green at low volume, yellow mid, orange/red at high
                r = min(255, int(volume * 2 * 255))
                g = min(255, int((1 - volume * 0.5) * 255))
                bar_color = (r, g, 50, 255)

            draw.rounded_rectangle(
                [(bar_margin, bar_y_start), (bar_margin + fill_width, bar_y_start + bar_height)],
                radius=2,
                fill=bar_color
            )

        # --- Icon in center area ---
        with self._lock:
            direction = self._scroll_direction

        if muted:
            icon = self._icon_muted
        elif direction == "up":
            icon = self._icon_plus
        elif direction == "down":
            icon = self._icon_minus
        else:
            icon = self._icon_normal

        # Icon area: below top label (~20px) to above the bar
        icon_area_top = 20
        icon_area_bottom = bar_y_start - 2
        icon_area_height = icon_area_bottom - icon_area_top
        icon_size = min(icon_area_height, 48)
        scaled = icon.resize((icon_size, icon_size), Image.Resampling.LANCZOS)

        icon_x = (width - icon_size) // 2
        icon_y = icon_area_top + (icon_area_height - icon_size) // 2
        img.paste(scaled, (icon_x, icon_y), scaled)

        del draw
        return img
