from src.backend.PluginManager.ActionBase import ActionBase
from src.backend.PluginManager.ActionBase import ActionBase
from src.backend.DeckManagement.DeckController import DeckController
from src.backend.PageManagement.Page import Page
from src.backend.PluginManager.PluginBase import PluginBase

import globals as gl
from loguru import logger as log
from fuzzywuzzy import fuzz

import os

class MuteKey(ActionBase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        self.plugin_base.volume_actions.append(self)

    def on_ready(self):
        self.current_state = -1
        self.on_tick()
        self.current_state = -1

    def on_tick(self):
        index = self.get_index()

        inputs = self.plugin_base.get_all_audio_items()
        if index < len(inputs):
            self.set_label(text=self.plugin_base.get_display_name(inputs[index]), position="center", font_size=10)
        else:
            self.clear()

    def clear(self):
        self.set_media(image=None)
        self.set_center_label(None)

    def on_key_down(self):
        # Toggle mute
        inputs = self.plugin_base.get_all_audio_items()

        index = self.get_index()
        if index >= len(inputs):
            return
        
        mute = inputs[index].mute == 0
        self.plugin_base.pulse.mute(obj=inputs[index], mute=mute)

    def get_index(self) -> int:
        start_index = self.plugin_base.start_index
        own_index = self.input_ident.coords[0]
        index = start_index + own_index - 1 # -1 because we want to ignore the first column containing the navigation keys
        return index