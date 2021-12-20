import PySimpleGUI as sg

import UI.UI_defaults as sgh
from db.Documents_db import DocumentDatabase


class CustomHeader(sg.Tab):
    def __init__(self, db, *args, **kwargs):
        super().__init__(element_justification=sgh.CENTER, *args, **kwargs)
        self.db = db

    def initialize(self):
        pass

    def reload(self):
        pass

    @property
    def callbacks(self):
        return {}

    def handle_enter(self, focused_element):
        pass

    def handle_event(self, event):
        self.callbacks.get(event, lambda: None)()
