import PySimpleGUI as sg

import gui.simple_gui_helper as sgh
from db.books_db import BookDatabase


class CustomTab(sg.Tab):
    """
    Custom tab in the books ui.
    """

    def __init__(self, db, *args, **kwargs):
        super().__init__(element_justification=sgh.CENTER, *args, **kwargs)
        self.db = db  # type: BookDatabase

    def initialize(self):
        """ Initialize the tab after it was first being drawn """
        pass

    def reload(self):
        """ Reload the tab using a whole new database data """
        pass

    @property
    def callbacks(self):
        """ Maps the different event keys to the handler functions """
        return {}

    def handle_enter(self, focused_element):
        """
        Handle an enter press.
        :param focused_element: The currently focused element
        """
        pass

    def handle_event(self, event):
        """
        Handle an event.
        :param event: The event key
        """
        self.callbacks.get(event, lambda: None)()
