from src.backend.PluginManager.ActionBase import ActionBase
from src.backend.PluginManager.ActionBase import ActionBase
from src.backend.DeckManagement.DeckController import DeckController
from src.backend.PageManagement.Page import Page
from src.backend.PluginManager.PluginBase import PluginBase

import globals as gl
from loguru import logger as log

import os
from PIL import Image, ImageEnhance

class UpKey(ActionBase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        self.plugin_base.volume_actions.append(self)

        self.current_state = -1

        self.icon_path = os.path.join(self.plugin_base.PATH, "assets", "volume_up.png")

    def on_ready(self):
        self.current_state = -1
        self.on_tick()
        self.current_state = -1

    def on_tick(self):
        index = self.get_index()

        inputs = self.plugin_base.get_all_audio_items()
        if index >= len(inputs):
            self.show_state(0)
        else:
            if self.can_go_higher():
                self.show_state(1)
            else:
                self.show_state(2)

    def can_go_higher(self) -> bool:
        index = self.get_index()
        inputs = self.plugin_base.get_all_audio_items()
        if index >= len(inputs):
            return False
        current_vol = inputs[index].volume.value_flat
        if current_vol < 1:
            return True
        return False

    def clear(self):
        if not self.showing_image:
            return
        self.set_media(image=None)
        self.set_bottom_label(None)

    def on_key_down(self):
        # Toggle mute
        inputs = self.plugin_base.get_all_audio_items()

        index = self.get_index()
        if index >= len(inputs):
            return
        
        volume = inputs[index].volume.value_flat
        volume += self.plugin_base.volume_increment

        self.plugin_base.pulse.volume_set_all_chans(obj=inputs[index], vol=min(1, volume))

    def get_index(self) -> int:
        start_index = self.plugin_base.start_index
        own_index = self.input_ident.coords[0]
        index = start_index + own_index - 1 # -1 because we want to ignore the first column containing the navigation keys
        return index
    
    def show_state(self, state: int) -> None:
        """
        0: No player
        1: Can go up
        2: Greyed out
        """
        # Don't do anything if the state hasn't changed
        if state == self.current_state:
            return
        self.current_state = state
        
        brightness = 1
        if state == 0:
            self.set_media(image=None)
            self.set_bottom_label(None)
        elif state == 1:
            self.set_bottom_label("Up", font_size=12)
            self.set_media(media_path=self.icon_path, size=0.8, valign=-1)
            return
        elif state == 2:
            brightness = 0.65
            self.set_bottom_label("Max", font_size=12)

            # Set image with modified brightness
            with Image.open(self.icon_path) as image:
                enhancer = ImageEnhance.Brightness(image)
                image = enhancer.enhance(brightness)
                self.set_media(image=image.copy(), size=0.8, valign=-1)