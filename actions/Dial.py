from src.backend.DeckManagement.InputIdentifier import Input
from src.backend.PluginManager.ActionBase import ActionBase
from src.backend.PluginManager.ActionBase import ActionBase
from src.backend.DeckManagement.DeckController import DeckController
from src.backend.PageManagement.Page import Page
from src.backend.PluginManager.PluginBase import PluginBase

import globals as gl
from loguru import logger as log
from fuzzywuzzy import fuzz
import math

import os

class Dial(ActionBase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        self.plugin_base.volume_actions.append(self)

    def on_ready(self):
        self.current_state = -1
        self.on_tick()
        self.current_state = -1

    def on_tick(self):
        index = self.get_index()

        inputs = self.plugin_base.pulse.sink_input_list()
        if index < len(inputs):
            self.update_labels()
        else:
            self.clear()

    def clear(self):
        self.set_media(image=None)
        self.set_top_label(None)
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

        elif event == Input.Dial.Events.TURN_CCW:
            volume = max(0, volume - self.plugin_base.volume_increment)
            self.plugin_base.pulse.volume_set_all_chans(obj=inputs[index], vol=volume)

        self.update_labels(volume=volume, muted=muted, name=name)

    def get_index(self) -> int:
        start_index = self.plugin_base.start_index
        own_index = int(self.input_ident.json_identifier)
        index = start_index + own_index
        return index

    def update_labels(self, volume=None, muted=None, name=None):
        if volume is None or muted is None or name is None:
            inputs = self.plugin_base.pulse.sink_input_list()
            index = self.get_index()
            if volume is None:
                volume = inputs[index].volume.value_flat
            if muted is None:
                muted = inputs[index].mute != 0
            if name is None:
                name = inputs[index].name

        if not muted:
            volumeLabel = str(math.ceil(volume * 100)) + "%"
            labelColor = [255, 255, 255]
        else:
            volumeLabel = "- " + self.plugin_base.lm.get("input.muted").upper() + " -"
            labelColor = [255, 0, 0]

        self.set_top_label(text=volumeLabel, color=labelColor, font_size=16, update=False)
        self.set_center_label(text=name, font_size=18)
        
